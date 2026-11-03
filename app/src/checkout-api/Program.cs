using System.Globalization;
using System.Net;

var builder = WebApplication.CreateBuilder(args);
var configured = builder.Configuration["PRICEBOOK_EFFECTIVE_FROM"]
    ?? throw new InvalidOperationException("PRICEBOOK_EFFECTIVE_FROM is required");
var books = configured.Split(';').Select(value =>
    DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture,
        DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var date)
        ? date : throw new InvalidOperationException("Invalid price book configuration"))
    .OrderDescending().ToArray();
var orderUrl = builder.Configuration["ORDER_SERVICE_URL"]
    ?? throw new InvalidOperationException("ORDER_SERVICE_URL is required");
builder.Services.AddHttpClient("orders", client =>
{
    client.BaseAddress = new Uri(orderUrl);
    client.Timeout = TimeSpan.FromSeconds(20);
});
var app = builder.Build();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapGet("/pricing/active", () => Results.Json(new
{
    active = books.Any(book => book <= DateTimeOffset.UtcNow)
}));
app.MapPost("/", async (HttpContext context, IHttpClientFactory clients, ILogger<Program> logger) =>
{
    var now = DateTimeOffset.UtcNow;
    var activeBook = books.Where(book => book <= now).Cast<DateTimeOffset?>().FirstOrDefault();
    if (activeBook is null)
    {
        logger.LogError("No active price book for {UtcNow:o}", now);
        context.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
        await context.Response.WriteAsJsonAsync(new { error = "No active price book" });
        return;
    }
    using var request = new HttpRequestMessage(HttpMethod.Post, "")
    {
        Content = new StreamContent(context.Request.Body)
    };
    request.Content.Headers.ContentType =
        System.Net.Http.Headers.MediaTypeHeaderValue.Parse(context.Request.ContentType ?? "application/json");
    request.Content.Headers.ContentLength = context.Request.ContentLength;
    try
    {
        using var response = await clients.CreateClient("orders").SendAsync(request, context.RequestAborted);
        context.Response.StatusCode = (int)response.StatusCode;
        context.Response.ContentType = response.Content.Headers.ContentType?.ToString() ?? "application/json";
        if (response.StatusCode >= HttpStatusCode.InternalServerError)
            logger.LogError("Order service returned HTTP {Status}", (int)response.StatusCode);
        await response.Content.CopyToAsync(context.Response.Body, context.RequestAborted);
    }
    catch (HttpRequestException error)
    {
        logger.LogError(error, "Order service request failed");
        context.Response.StatusCode = StatusCodes.Status502BadGateway;
        await context.Response.WriteAsJsonAsync(new { error = "Order service unavailable" });
    }
    catch (TaskCanceledException error) when (!context.RequestAborted.IsCancellationRequested)
    {
        logger.LogError(error, "Order service request timed out");
        context.Response.StatusCode = StatusCodes.Status504GatewayTimeout;
        await context.Response.WriteAsJsonAsync(new { error = "Order service timeout" });
    }
});
app.Run();
