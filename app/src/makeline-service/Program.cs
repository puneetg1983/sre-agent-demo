using System.Net;
using System.Text.Json;
using Azure.Identity;
using Azure.Messaging.ServiceBus;
using Microsoft.Azure.Cosmos;
using Newtonsoft.Json;

var builder = WebApplication.CreateBuilder(args);
string Required(string key) => builder.Configuration[key]
    ?? throw new InvalidOperationException($"{key} is required");
var credential = new DefaultAzureCredential();
builder.Services.AddSingleton(new CosmosClient(Required("AZURE_COSMOS_RESOURCEENDPOINT"), credential,
    new CosmosClientOptions { ConnectionMode = ConnectionMode.Gateway }));
builder.Services.AddSingleton(service => service.GetRequiredService<CosmosClient>()
    .GetContainer(Required("ORDER_DB_NAME"), Required("ORDER_DB_CONTAINER_NAME")));
builder.Services.AddSingleton(new ServiceBusClient(Required("AZURE_SERVICEBUS_FULLYQUALIFIEDNAMESPACE"), credential));
builder.Services.AddSingleton(service => service.GetRequiredService<ServiceBusClient>()
    .CreateReceiver(Required("ORDER_QUEUE_NAME")));
builder.Services.AddHostedService<OrderConsumer>();
var app = builder.Build();
app.Use(async (context, next) =>
{
    try
    {
        await next(context);
    }
    catch (CosmosException error)
    {
        app.Logger.LogError(error, "Cosmos operation failed with HTTP {Status}", (int)error.StatusCode);
        context.Response.StatusCode = 500;
        await context.Response.WriteAsJsonAsync(new { error = "Order database unavailable" });
    }
});
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapGet("/liveness", () => Results.Ok(new { status = "alive" }));
app.MapGet("/order/recent", async (Container container, HttpResponse response, CancellationToken cancellation) =>
{
    response.Headers.CacheControl = "no-store";
    var orders = new List<Order>();
    using var iterator = container.GetItemQueryIterator<Order>(
        new QueryDefinition("SELECT TOP @limit * FROM o ORDER BY o._ts DESC").WithParameter("@limit", 15),
        requestOptions: new QueryRequestOptions { PartitionKey = new PartitionKey("contoso"), MaxItemCount = 15 });
    while (iterator.HasMoreResults)
        orders.AddRange(await iterator.ReadNextAsync(cancellation));
    return Results.Ok(orders);
});
app.MapGet("/order/fetch", async (Container container, CancellationToken cancellation) =>
{
    var orders = new List<Order>();
    using var iterator = container.GetItemQueryIterator<Order>(
        new QueryDefinition("SELECT * FROM o WHERE o.status = @status").WithParameter("@status", 0),
        requestOptions: new QueryRequestOptions { PartitionKey = new PartitionKey("contoso") });
    while (iterator.HasMoreResults)
        orders.AddRange(await iterator.ReadNextAsync(cancellation));
    return Results.Ok(orders);
});
app.MapGet("/order/{id}", async (string id, Container container, CancellationToken cancellation) =>
{
    try
    {
        var response = await container.ReadItemAsync<Order>(id, new PartitionKey("contoso"), cancellationToken: cancellation);
        return Results.Ok(response.Resource);
    }
    catch (CosmosException error) when (error.StatusCode == HttpStatusCode.NotFound)
    {
        return Results.NotFound(new { error = "Order not found" });
    }
});
app.MapPut("/order", async (Order order, Container container, CancellationToken cancellation) =>
{
    if (string.IsNullOrWhiteSpace(order.OrderId) || order.Status is < 0 or > 2)
        return Results.BadRequest(new { error = "A valid orderId and status 0..2 are required" });
    await container.PatchItemAsync<Order>(order.OrderId, new PartitionKey("contoso"),
        [PatchOperation.Set("/status", order.Status)], cancellationToken: cancellation);
    return Results.Accepted();
});
app.Run();

public sealed class OrderConsumer(ServiceBusReceiver receiver, Container container, ILogger<OrderConsumer> logger)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var messages = await receiver.ReceiveMessagesAsync(10, TimeSpan.FromSeconds(5), stoppingToken);
                foreach (var message in messages)
                {
                    using var envelope = JsonDocument.Parse(message.Body.ToMemory());
                    // The upstream sender encodes the order as an AMQP string.
                    var json = envelope.RootElement.ValueKind == JsonValueKind.String
                        ? envelope.RootElement.GetString()! : envelope.RootElement.GetRawText();
                    var order = System.Text.Json.JsonSerializer.Deserialize<Order>(json,
                        new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                    if (order is null || string.IsNullOrWhiteSpace(order.OrderId))
                    {
                        logger.LogError("Invalid order in message {MessageId}", message.MessageId);
                        await receiver.DeadLetterMessageAsync(message, "InvalidOrder", cancellationToken: stoppingToken);
                        continue;
                    }
                    order.Id = order.OrderId;
                    order.StoreId = "contoso";
                    order.Status = 0;
                    try
                    {
                        await container.CreateItemAsync(order, new PartitionKey("contoso"), cancellationToken: stoppingToken);
                    }
                    catch (CosmosException error) when (error.StatusCode == HttpStatusCode.Conflict)
                    {
                        logger.LogInformation("Order {OrderId} already persisted; completing duplicate delivery", order.OrderId);
                    }
                    await receiver.CompleteMessageAsync(message, stoppingToken);
                    logger.LogInformation("Persisted order {OrderId}", order.OrderId);
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (CosmosException error)
            {
                logger.LogError(error, "Cosmos persistence failed with HTTP {Status}; message remains unacknowledged", (int)error.StatusCode);
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
            catch (ServiceBusException error)
            {
                logger.LogError(error, "Service Bus receive failed: {Reason}", error.Reason);
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
            catch (System.Text.Json.JsonException error)
            {
                logger.LogError(error, "Malformed order message; delivery remains unacknowledged");
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
        }
    }
}

public sealed class Order
{
    [JsonProperty("id")]
    public string Id { get; set; } = "";
    [JsonProperty("orderId")]
    public string OrderId { get; set; } = "";
    [JsonProperty("storeId")]
    public string StoreId { get; set; } = "contoso";
    [JsonProperty("customerId")]
    public string CustomerId { get; set; } = "";
    [JsonProperty("items")]
    public List<Item> Items { get; set; } = [];
    [JsonProperty("status")]
    public int Status { get; set; }
    [JsonProperty("_ts")]
    public long UpdatedAtUnixSeconds { get; set; }
}

public sealed class Item
{
    [JsonProperty("productId")]
    public int ProductId { get; set; }
    [JsonProperty("quantity")]
    public int Quantity { get; set; }
    [JsonProperty("price")]
    public decimal Price { get; set; }
}
