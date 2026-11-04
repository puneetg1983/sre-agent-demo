using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using Microsoft.Data.SqlClient;

static class SqlOperations
{
    static string Required(string name) =>
        Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
            ? value : throw new InvalidOperationException($"{name} is required");

    public static SqlConnection Connection(string application) => new(new SqlConnectionStringBuilder
    {
        DataSource = $"tcp:{Required("SQL_SERVER")},1433",
        InitialCatalog = Required("SQL_DATABASE"),
        Authentication = SqlAuthenticationMethod.ActiveDirectoryWorkloadIdentity,
        UserID = Required("AZURE_CLIENT_ID"),
        Encrypt = SqlConnectionEncryptOption.Mandatory,
        TrustServerCertificate = false,
        ConnectTimeout = 15,
        ConnectRetryCount = 0,
        ApplicationName = application,
        MaxPoolSize = 10
    }.ConnectionString);

    public static async Task BootstrapAsync()
    {
        using var cancellation = new CancellationTokenSource();
        Console.CancelKeyPress += (_, e) => { e.Cancel = true; cancellation.Cancel(); };
        using var termination = OperatingSystem.IsLinux()
            ? PosixSignalRegistration.Create(PosixSignal.SIGTERM, ctx => { ctx.Cancel = true; cancellation.Cancel(); })
            : null;
        // Federation and the SQL Entra administrator can take several minutes to propagate.
        for (var attempt = 1; ; attempt++)
        {
            try { await BootstrapAsync(cancellation.Token); break; }
            catch (SqlException error) when (attempt < 20)
            {
                Console.Error.WriteLine($"SQL bootstrap attempt {attempt} failed ({error.Number}): {error.Message}");
                await Task.Delay(TimeSpan.FromSeconds(15), cancellation.Token);
            }
        }
    }

    static async Task BootstrapAsync(CancellationToken token)
    {
        var catalogJson = await File.ReadAllTextAsync(Required("CATALOG_SEED_PATH"), token);
        CatalogBootstrap.Validate(catalogJson);
        var productClientId = Guid.Parse(Required("PRODUCT_SERVICE_CLIENT_ID"));
        await using var connection = Connection("Contoso.SqlBootstrap");
        await connection.OpenAsync(token);
        var script = await File.ReadAllTextAsync(Path.Combine(AppContext.BaseDirectory, "bootstrap.sql"), token);
        foreach (var batch in Regex.Split(script, @"^\s*GO\s*$", RegexOptions.Multiline | RegexOptions.IgnoreCase))
        {
            if (string.IsNullOrWhiteSpace(batch)) continue;
            using var command = new SqlCommand(batch, connection) { CommandTimeout = 120 };
            await command.ExecuteNonQueryAsync(token);
        }
        // CREATE USER ... WITH SID uses the client ID for service principals and managed identities.
        var principal = Guid.Parse(Required("INVENTORY_SERVICE_CLIENT_ID"));
        var sid = "0x" + Convert.ToHexString(principal.ToByteArray());
        using var user = new SqlCommand($"""
            IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'inventory-service')
                CREATE USER [inventory-service] WITH SID = {sid}, TYPE = E;
            IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'inventory-service' AND sid = {sid})
                THROW 51000, 'Existing inventory-service user has a different identity; refusing to reassign permissions.', 1;
            GRANT EXECUTE ON OBJECT::dbo.GetPickupAvailability TO [inventory-service];
            """, connection) { CommandTimeout = 30 };
        await user.ExecuteNonQueryAsync(token);
        await CatalogBootstrap.RunAsync(connection, catalogJson, productClientId, token);
        Console.WriteLine("SQL_BOOTSTRAP_COMPLETE schema seeded; inventory-service has EXECUTE only.");
    }
}
