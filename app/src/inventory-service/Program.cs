using System.Data;
using System.Diagnostics;
using Azure.Identity;
using Microsoft.ApplicationInsights.DependencyCollector;
using Microsoft.ApplicationInsights.Extensibility;
using Microsoft.Data.SqlClient;

if (args.Length > 0 && !args[0].StartsWith('-'))
{
    if (args.Length != 1 || args[0] != "bootstrap")
        throw new ArgumentException("Expected 'bootstrap' or web host options.");
    await SqlOperations.BootstrapAsync();
    return;
}

var builder = WebApplication.CreateBuilder(args);
builder.Logging.AddJsonConsole();
builder.Services.AddApplicationInsightsTelemetry(options =>
{
    options.ConnectionString = Environment.GetEnvironmentVariable("APPINSIGHTS_CONNECTION_STRING");
    options.EnableAdaptiveSampling = false;
});
builder.Services.AddSingleton<ITelemetryInitializer, InventoryRole>();
builder.Services.Configure<TelemetryConfiguration>(configuration =>
    configuration.SetAzureTokenCredential(new WorkloadIdentityCredential()));
builder.Services.ConfigureTelemetryModule<DependencyTrackingTelemetryModule>((module, _) =>
    module.EnableSqlCommandTextInstrumentation = true);
var app = builder.Build();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapGet("/pickup/{productId:int:min(1)}", async (int productId, HttpContext context, ILogger<Program> logger) =>
{
    var timer = Stopwatch.StartNew();
    long connectMs = 0;
    long queryMs = 0;
    int? sessionId = null;
    var outcome = "error";
    try
    {
        await using var connection = SqlOperations.Connection("Contoso.Pickup");
        await connection.OpenAsync(context.RequestAborted);
        connectMs = timer.ElapsedMilliseconds;
        using (var session = new SqlCommand("SELECT @@SPID", connection) { CommandTimeout = 8 })
            sessionId = Convert.ToInt32(await session.ExecuteScalarAsync(context.RequestAborted));
        using var command = new SqlCommand("dbo.GetPickupAvailability", connection)
        {
            CommandType = CommandType.StoredProcedure,
            CommandTimeout = 8
        };
        command.Parameters.Add("@ProductId", SqlDbType.Int).Value = productId;
        var queryTimer = Stopwatch.StartNew();
        try
        {
            await using var reader = await command.ExecuteReaderAsync(context.RequestAborted);
            if (!await reader.ReadAsync(context.RequestAborted))
            {
                outcome = "not_found";
                return Results.NotFound(new { error = "No pickup inventory for this product." });
            }
            outcome = "ok";
            return Results.Ok(new
            {
                productId = reader.GetInt32(0),
                availableQuantity = reader.GetInt32(1),
                storeName = reader.GetString(2),
                readyInMinutes = reader.GetInt32(3)
            });
        }
        finally { queryMs = queryTimer.ElapsedMilliseconds; }
    }
    catch (SqlException error)
    {
        outcome = error.Number == -2 ? "sql_timeout" : "sql_error";
        logger.LogError(error, "Pickup SQL failure {SqlErrorNumber}; trace {TraceId}",
            error.Number, Activity.Current?.TraceId.ToString());
        return Results.Json(new
        {
            error = "Pickup availability is temporarily unavailable. Shopping and checkout still work.",
            code = outcome,
            traceId = Activity.Current?.TraceId.ToString()
        }, statusCode: 503);
    }
    catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested)
    {
        outcome = "cancelled";
        return Results.StatusCode(499);
    }
    finally
    {
        logger.LogInformation(
            "SQL_PICKUP_REQUEST ProductId={ProductId} DurationMs={DurationMs} ConnectMs={ConnectMs} QueryMs={QueryMs} Outcome={Outcome} SessionId={SessionId} TraceId={TraceId}",
            productId, timer.ElapsedMilliseconds, connectMs, queryMs, outcome, sessionId,
            Activity.Current?.TraceId.ToString());
    }
});
app.Run();

sealed class InventoryRole : ITelemetryInitializer
{
    public void Initialize(Microsoft.ApplicationInsights.Channel.ITelemetry telemetry) =>
        telemetry.Context.Cloud.RoleName = "inventory-service";
}
