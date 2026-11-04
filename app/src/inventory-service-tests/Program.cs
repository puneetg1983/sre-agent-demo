using System.Data;
using System.Text.Json;
using Azure.Identity;
using Microsoft.Data.SqlClient;

var catalogPath = args.Length > 0 ? args[0] : "app/src/product-service/catalog.json";
var json = await File.ReadAllTextAsync(catalogPath);
CatalogBootstrap.Validate(json);
var products = JsonSerializer.Deserialize<List<Dictionary<string, JsonElement>>>(json)!;
foreach (var mutation in new Action<List<Dictionary<string, JsonElement>>>[] {
    p => p[1]["id"] = p[0]["id"],
    p => p[0]["category"] = JsonSerializer.SerializeToElement(" "),
    p => p[0]["category"] = JsonSerializer.SerializeToElement(new string('x', 101)),
    p => p[0]["price"] = JsonSerializer.SerializeToElement(-1),
}) {
    var changed = JsonSerializer.Deserialize<List<Dictionary<string, JsonElement>>>(json)!;
    mutation(changed);
    try { CatalogBootstrap.Validate(JsonSerializer.Serialize(changed)); throw new Exception("Invalid catalog accepted"); }
    catch (InvalidOperationException) { }
}
Console.WriteLine($"PASS: canonical catalog validation ({products.Count} products), duplicate IDs, category limits and negative prices.");

if (Environment.GetEnvironmentVariable("CATALOG_SQL_INTEGRATION_TEST") != "1") return;
var database = Environment.GetEnvironmentVariable("SQL_DATABASE") ?? "";
if (!database.EndsWith("_test", StringComparison.Ordinal))
    throw new InvalidOperationException("Integration tests require an isolated *_test database.");
var clientId = Guid.Parse(Environment.GetEnvironmentVariable("PRODUCT_SERVICE_CLIENT_ID")!);
await using var connection = new SqlConnection(new SqlConnectionStringBuilder {
    DataSource = Environment.GetEnvironmentVariable("SQL_SERVER"),
    InitialCatalog = database, Encrypt = SqlConnectionEncryptOption.Mandatory,
    Authentication = SqlAuthenticationMethod.ActiveDirectoryWorkloadIdentity,
    UserID = Environment.GetEnvironmentVariable("AZURE_CLIENT_ID")
}.ConnectionString);
await connection.OpenAsync();
using (var schema = new SqlCommand("""
    IF OBJECT_ID(N'dbo.PickupInventory') IS NULL
        CREATE TABLE dbo.PickupInventory (ProductId int PRIMARY KEY, AvailableQuantity int,
            StoreName nvarchar(100), ReadyInMinutes int);
    """, connection)) await schema.ExecuteNonQueryAsync();
await CatalogBootstrap.RunAsync(connection, json, clientId, default);
using (var edit = new SqlCommand("""
    UPDATE dbo.Products SET Name=N'Edited fixture', Category=N'Edited' WHERE Id=1;
    UPDATE dbo.PickupInventory SET AvailableQuantity=7, ReadyInMinutes=60 WHERE ProductId=1;
    DELETE dbo.Products WHERE Id=2;
    """, connection)) await edit.ExecuteNonQueryAsync();
await CatalogBootstrap.RunAsync(connection, json, clientId, default);
using var verify = new SqlCommand("""
    IF NOT EXISTS (SELECT 1 FROM dbo.Products WHERE Id=1 AND Name=N'Edited fixture' AND Category=N'Edited')
        THROW 51010, 'Bootstrap overwrote catalog edits', 1;
    IF EXISTS (SELECT 1 FROM dbo.Products WHERE Id=2)
        THROW 51011, 'Bootstrap resurrected a deleted product', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.PickupInventory WHERE ProductId=1 AND AvailableQuantity=7 AND ReadyInMinutes=60)
        THROW 51012, 'Bootstrap overwrote pickup stock/settings', 1;
    IF EXISTS (SELECT Id FROM dbo.Products EXCEPT SELECT ProductId FROM dbo.PickupInventory)
        THROW 51013, 'Catalog product has no pickup inventory', 1;
    EXECUTE AS USER = 'product-service';
    DECLARE @Allowed int = HAS_PERMS_BY_NAME('dbo.Products', 'OBJECT', 'INSERT'),
            @Inventory int = HAS_PERMS_BY_NAME('dbo.PickupInventory', 'OBJECT', 'UPDATE'),
            @DDL int = HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CREATE TABLE');
    REVERT;
    IF @Allowed <> 1 OR @Inventory <> 0 OR @DDL <> 0
        THROW 51014, 'Catalog permissions are not narrowly scoped', 1;
    """, connection);
await verify.ExecuteNonQueryAsync();
Console.WriteLine("PASS: live isolated SQL bootstrap idempotence, edit/delete preservation, pickup coverage and narrow grants.");
