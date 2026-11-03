IF OBJECT_ID('dbo.PickupInventory', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.PickupInventory (
        ProductId int NOT NULL PRIMARY KEY,
        AvailableQuantity int NOT NULL CHECK (AvailableQuantity >= 0),
        StoreName nvarchar(100) NOT NULL,
        ReadyInMinutes int NOT NULL,
        LastReconciledAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO
INSERT INTO dbo.PickupInventory (ProductId, AvailableQuantity, StoreName, ReadyInMinutes)
SELECT v.ProductId, 10 + v.ProductId, N'Contoso Central', 30
FROM (VALUES (1),(2),(3),(4),(5),(6),(7),(8),(9),(10)) v(ProductId)
WHERE NOT EXISTS (SELECT 1 FROM dbo.PickupInventory p WHERE p.ProductId = v.ProductId);
GO
CREATE OR ALTER PROCEDURE dbo.GetPickupAvailability @ProductId int
AS
BEGIN
    SET NOCOUNT ON;
    SELECT ProductId, AvailableQuantity, StoreName, ReadyInMinutes
    FROM dbo.PickupInventory
    WHERE ProductId = @ProductId;
END;
GO
ALTER DATABASE CURRENT SET QUERY_STORE = ON (
    OPERATION_MODE = READ_WRITE,
    MAX_STORAGE_SIZE_MB = 100,
    INTERVAL_LENGTH_MINUTES = 1,
    WAIT_STATS_CAPTURE_MODE = ON
);
