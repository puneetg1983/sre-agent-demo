using System.Text.Json;
using Azure;
using Azure.Identity;
using Azure.Messaging.ServiceBus;

var builder = WebApplication.CreateBuilder(args);
string Required(string name) => builder.Configuration[name]
    ?? throw new InvalidOperationException($"{name} is required");
builder.Services.AddSingleton(new ServiceBusClient(Required("ORDER_QUEUE_HOSTNAME"),
    new DefaultAzureCredential(), new ServiceBusClientOptions
    {
        RetryOptions = new ServiceBusRetryOptions
        {
            MaxRetries = 1,
            TryTimeout = TimeSpan.FromSeconds(5),
            Delay = TimeSpan.FromMilliseconds(500),
            MaxDelay = TimeSpan.FromSeconds(1)
        }
    }));
builder.Services.AddSingleton(service => service.GetRequiredService<ServiceBusClient>()
    .CreateSender(Required("ORDER_QUEUE_NAME")));
var app = builder.Build();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapPost("/", async (HttpContext context, ServiceBusSender sender, ILogger<Program> logger) =>
{
    JsonDocument document;
    try
    {
        document = await JsonDocument.ParseAsync(context.Request.Body, cancellationToken: context.RequestAborted);
    }
    catch (JsonException error)
    {
        logger.LogWarning(error, "Invalid order JSON");
        return Results.BadRequest(new { error = "A JSON order is required" });
    }
    using (document)
    {
        if (document.RootElement.ValueKind != JsonValueKind.Object
            || !document.RootElement.TryGetProperty("orderId", out var id)
            || id.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(id.GetString()) || id.GetString()!.Length > 128)
        {
            logger.LogWarning("Order has a missing or invalid orderId");
            return Results.BadRequest(new { error = "A nonempty orderId of at most 128 characters is required" });
        }
        try
        {
            var message = new ServiceBusMessage(BinaryData.FromString(document.RootElement.GetRawText()))
            {
                MessageId = id.GetString(),
                ContentType = "application/json"
            };
            await sender.SendMessageAsync(message, context.RequestAborted);
            logger.LogInformation("Accepted order {OrderId}", message.MessageId);
            return Results.StatusCode(StatusCodes.Status201Created);
        }
        catch (UnauthorizedAccessException error)
        {
            logger.LogError(error, "Service Bus denied Send authorization");
        }
        catch (ServiceBusException error)
        {
            logger.LogError(error, "Service Bus send failed: {Reason}", error.Reason);
        }
        catch (RequestFailedException error)
        {
            logger.LogError(error, "Service Bus request failed with HTTP {Status}", error.Status);
        }
        catch (AuthenticationFailedException error)
        {
            logger.LogError(error, "Workload identity authentication failed");
        }
        return Results.Json(new { error = "Order queue unavailable" },
            statusCode: StatusCodes.Status500InternalServerError);
    }
});
app.Run();
