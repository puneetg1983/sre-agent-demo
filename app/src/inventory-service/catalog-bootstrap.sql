SET XACT_ABORT ON;
DECLARE @LockResult int;
EXEC @LockResult = sys.sp_getapplock
    @Resource = N'Contoso.CatalogBootstrap', @LockMode = N'Exclusive',
    @LockOwner = N'Transaction', @LockTimeout = 30000;
IF @LockResult < 0 THROW 51001, 'Could not acquire catalog bootstrap lock.', 1;

IF OBJECT_ID(N'dbo.Products', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Products (
        Id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Name nvarchar(200) NOT NULL,
        Price real NOT NULL CHECK (Price >= 0),
        Description nvarchar(4000) NOT NULL,
        Image nvarchar(2048) NOT NULL,
        Category nvarchar(100) NOT NULL DEFAULT N'General',
        CONSTRAINT CK_Products_Category CHECK (LEN(LTRIM(RTRIM(Category))) > 0)
    );
END;

-- A ledger distinguishes a newly introduced seed from an intentionally deleted product.
IF OBJECT_ID(N'dbo.CatalogSeedHistory', N'U') IS NULL
    CREATE TABLE dbo.CatalogSeedHistory (ProductId int NOT NULL PRIMARY KEY);

DECLARE @Seed TABLE (
    Id int NOT NULL PRIMARY KEY, Name nvarchar(200) NOT NULL, Price real NOT NULL,
    Description nvarchar(4000) NOT NULL, Image nvarchar(2048) NOT NULL, Category nvarchar(100) NOT NULL
);
INSERT @Seed (Id, Name, Price, Description, Image, Category)
SELECT Id, Name, Price, Description, Image, Category
FROM OPENJSON(@CatalogJson) WITH (
    Id int '$.id', Name nvarchar(200) '$.name', Price real '$.price',
    Description nvarchar(4000) '$.description', Image nvarchar(2048) '$.image',
    Category nvarchar(100) '$.category'
);

SET IDENTITY_INSERT dbo.Products ON;
INSERT dbo.Products (Id, Name, Price, Description, Image, Category)
SELECT s.Id, s.Name, s.Price, s.Description, s.Image, s.Category FROM @Seed s
WHERE NOT EXISTS (SELECT 1 FROM dbo.Products p WITH (UPDLOCK, HOLDLOCK) WHERE p.Id = s.Id)
  AND NOT EXISTS (SELECT 1 FROM dbo.CatalogSeedHistory h WHERE h.ProductId = s.Id);
SET IDENTITY_INSERT dbo.Products OFF;

INSERT dbo.CatalogSeedHistory (ProductId)
SELECT s.Id FROM @Seed s WHERE NOT EXISTS (
    SELECT 1 FROM dbo.CatalogSeedHistory h WHERE h.ProductId = s.Id
);

-- Seed missing pickup rows only; never reset existing quantities or store settings.
INSERT dbo.PickupInventory (ProductId, AvailableQuantity, StoreName, ReadyInMinutes)
SELECT s.Id, 10 + s.Id, N'Contoso Central', 30 FROM @Seed s
WHERE EXISTS (SELECT 1 FROM dbo.Products p WHERE p.Id = s.Id)
  AND NOT EXISTS (SELECT 1 FROM dbo.PickupInventory p WITH (UPDLOCK, HOLDLOCK) WHERE p.ProductId = s.Id);
