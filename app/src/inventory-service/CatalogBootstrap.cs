using System.Data;
using System.Text.Json;
using Microsoft.Data.SqlClient;

static class CatalogBootstrap
{
    public static void Validate(string json)
    {
        using var document = JsonDocument.Parse(json);
        if (document.RootElement.ValueKind != JsonValueKind.Array || document.RootElement.GetArrayLength() == 0)
            throw new InvalidOperationException("Catalog must be a nonempty JSON array.");
        var ids = new HashSet<int>();
        foreach (var product in document.RootElement.EnumerateArray())
        {
            if (!product.GetProperty("id").TryGetInt32(out var id) || id < 1 || !ids.Add(id))
                throw new InvalidOperationException("Catalog IDs must be positive, unique integers.");
            foreach (var (name, limit) in new[] { ("name", 200), ("description", 4000), ("image", 2048), ("category", 100) })
            {
                var value = product.GetProperty(name).GetString();
                if (string.IsNullOrWhiteSpace(value) || value.Length > limit)
                    throw new InvalidOperationException($"Catalog field {name} is empty or too long.");
            }
            if (!product.GetProperty("price").TryGetSingle(out var price) || !float.IsFinite(price) || price < 0)
                throw new InvalidOperationException("Catalog price must be finite and nonnegative.");
        }
    }

    public static async Task RunAsync(SqlConnection connection, string json, Guid clientId, CancellationToken token)
    {
        Validate(json);
        await using var transaction = (SqlTransaction)await connection.BeginTransactionAsync(token);
        var script = await File.ReadAllTextAsync(Path.Combine(AppContext.BaseDirectory, "catalog-bootstrap.sql"), token);
        using (var seed = new SqlCommand(script, connection, transaction) { CommandTimeout = 120 })
        {
            seed.Parameters.Add("@CatalogJson", SqlDbType.NVarChar, -1).Value = json;
            await seed.ExecuteNonQueryAsync(token);
        }
        var sid = "0x" + Convert.ToHexString(clientId.ToByteArray());
        using var grant = new SqlCommand($"""
            IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'product-service')
                CREATE USER [product-service] WITH SID = {sid}, TYPE = E;
            IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'product-service' AND sid = {sid})
                THROW 51002, 'Existing product-service identity does not match; refusing permission reassignment.', 1;
            GRANT SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.Products TO [product-service];
            DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.PickupInventory TO [product-service];
            DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.CatalogSeedHistory TO [product-service];
            DENY CREATE TABLE, ALTER ANY SCHEMA TO [product-service];
            """, connection, transaction) { CommandTimeout = 30 };
        await grant.ExecuteNonQueryAsync(token);
        await transaction.CommitAsync(token);
        Console.WriteLine("CATALOG_BOOTSTRAP_COMPLETE missing catalog/pickup rows seeded; product-service has catalog-only DML.");
    }
}
