use crate::models::{Product, ProductStore, StoreError, seed_products, validate_product};
use std::{
    sync::RwLock,
    time::{Duration, Instant},
};
use tiberius::{AuthMethod, Client, Config, Row};
use tokio::{net::TcpStream, sync::Mutex};
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

pub enum CatalogStore {
    Memory(RwLock<ProductStore>),
    Sql(SqlStore),
}

impl CatalogStore {
    pub fn memory() -> Self {
        Self::Memory(RwLock::new(ProductStore::new(seed_products())))
    }

    pub fn sql() -> std::io::Result<Self> {
        Ok(Self::Sql(SqlStore {
            server: required("SQL_SERVER")?,
            database: required("SQL_DATABASE")?,
            client_id: required("AZURE_CLIENT_ID")?,
            tenant_id: required("AZURE_TENANT_ID")?,
            token_file: required("AZURE_FEDERATED_TOKEN_FILE")?,
            http: reqwest::Client::builder()
                .timeout(Duration::from_secs(10))
                .build()
                .map_err(std::io::Error::other)?,
            token: Mutex::new(None),
        }))
    }

    pub async fn list(&self) -> Result<Vec<Product>, StoreError> {
        match self {
            Self::Memory(store) => Ok(store.read().map_err(unavailable)?.list().to_vec()),
            Self::Sql(store) => store.query("SELECT Id, Name, Price, Description, Image, Category FROM dbo.Products ORDER BY Id", &[]).await,
        }
    }

    pub async fn find(&self, id: i32) -> Result<Product, StoreError> {
        match self {
            Self::Memory(store) => store.read().map_err(unavailable)?.find(id).cloned(),
            Self::Sql(store) => store.query("SELECT Id, Name, Price, Description, Image, Category FROM dbo.Products WHERE Id = @P1", &[&id])
                .await?.into_iter().next().ok_or(StoreError::NotFound(id)),
        }
    }

    pub async fn insert(&self, product: Product) -> Result<Product, StoreError> {
        validate_product(&product)?;
        match self {
            Self::Memory(store) => store.write().map_err(unavailable)?.insert(product),
            Self::Sql(store) => store.query(
                "INSERT dbo.Products (Name, Price, Description, Image, Category) OUTPUT INSERTED.Id, INSERTED.Name, INSERTED.Price, INSERTED.Description, INSERTED.Image, INSERTED.Category VALUES (@P1, @P2, @P3, @P4, @P5)",
                &[&product.name, &product.price, &product.description, &product.image, &product.category])
                .await?.into_iter().next().ok_or(StoreError::Unavailable),
        }
    }

    pub async fn update(&self, product: Product) -> Result<Product, StoreError> {
        validate_product(&product)?;
        match self {
            Self::Memory(store) => store.write().map_err(unavailable)?.update(product),
            Self::Sql(store) => store.query(
                "UPDATE dbo.Products SET Name=@P1, Price=@P2, Description=@P3, Image=@P4, Category=@P5 OUTPUT INSERTED.Id, INSERTED.Name, INSERTED.Price, INSERTED.Description, INSERTED.Image, INSERTED.Category WHERE Id=@P6",
                &[&product.name, &product.price, &product.description, &product.image, &product.category, &product.id])
                .await?.into_iter().next().ok_or(StoreError::NotFound(product.id)),
        }
    }

    pub async fn delete(&self, id: i32) -> Result<(), StoreError> {
        match self {
            Self::Memory(store) => store.write().map_err(unavailable)?.delete(id),
            Self::Sql(store) => store.query(
                "DELETE dbo.Products OUTPUT DELETED.Id, DELETED.Name, DELETED.Price, DELETED.Description, DELETED.Image, DELETED.Category WHERE Id=@P1", &[&id])
                .await?.into_iter().next().map(|_| ()).ok_or(StoreError::NotFound(id)),
        }
    }
}

fn required(name: &str) -> std::io::Result<String> {
    std::env::var(name)
        .ok()
        .filter(|v| !v.trim().is_empty())
        .ok_or_else(|| {
            std::io::Error::other(format!("{name} is required for SQL catalog persistence"))
        })
}

fn unavailable(error: impl std::fmt::Display) -> StoreError {
    log::error!("Catalog SQL/storage operation failed: {error}");
    StoreError::Unavailable
}

pub struct SqlStore {
    server: String,
    database: String,
    client_id: String,
    tenant_id: String,
    token_file: String,
    http: reqwest::Client,
    token: Mutex<Option<(String, Instant)>>,
}

#[derive(serde::Deserialize)]
struct TokenResponse {
    access_token: String,
    expires_in: u64,
}

impl SqlStore {
    async fn access_token(&self) -> Result<String, StoreError> {
        let mut cached = self.token.lock().await;
        if let Some((token, expires)) = cached.as_ref()
            && *expires > Instant::now() + Duration::from_secs(120)
        {
            return Ok(token.clone());
        }
        let assertion = tokio::fs::read_to_string(&self.token_file)
            .await
            .map_err(unavailable)?;
        let response = self
            .http
            .post(format!(
                "https://login.microsoftonline.com/{}/oauth2/v2.0/token",
                self.tenant_id
            ))
            .form(&[
                ("client_id", self.client_id.as_str()),
                ("scope", "https://database.windows.net/.default"),
                ("grant_type", "client_credentials"),
                (
                    "client_assertion_type",
                    "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                ),
                ("client_assertion", assertion.trim()),
            ])
            .send()
            .await
            .map_err(unavailable)?
            .error_for_status()
            .map_err(unavailable)?
            .json::<TokenResponse>()
            .await
            .map_err(unavailable)?;
        *cached = Some((
            response.access_token.clone(),
            Instant::now() + Duration::from_secs(response.expires_in),
        ));
        Ok(response.access_token)
    }

    async fn connect(&self) -> Result<Client<Compat<TcpStream>>, StoreError> {
        let mut config = Config::new();
        config.host(&self.server);
        config.port(1433);
        config.database(&self.database);
        config.application_name("Contoso.Catalog");
        config.authentication(AuthMethod::AADToken(self.access_token().await?));
        // TLS certificate validation stays enabled; Azure SQL must use its DNS hostname.
        let tcp = TcpStream::connect(config.get_addr())
            .await
            .map_err(unavailable)?;
        tcp.set_nodelay(true).map_err(unavailable)?;
        Client::connect(config, tcp.compat_write())
            .await
            .map_err(unavailable)
    }

    async fn query(
        &self,
        sql: &str,
        params: &[&dyn tiberius::ToSql],
    ) -> Result<Vec<Product>, StoreError> {
        tokio::time::timeout(Duration::from_secs(15), async {
            let mut connection = self.connect().await?;
            let rows = connection
                .query(sql, params)
                .await
                .map_err(unavailable)?
                .into_first_result()
                .await
                .map_err(unavailable)?;
            rows.iter().map(product_from_row).collect()
        })
        .await
        .map_err(unavailable)?
    }
}

fn product_from_row(row: &Row) -> Result<Product, StoreError> {
    fn text(row: &Row, index: usize) -> Result<String, StoreError> {
        row.try_get::<&str, _>(index)
            .map_err(unavailable)?
            .map(str::to_owned)
            .ok_or(StoreError::Unavailable)
    }

    Ok(Product {
        id: row
            .try_get(0)
            .map_err(unavailable)?
            .ok_or(StoreError::Unavailable)?,
        name: text(row, 1)?,
        price: row
            .try_get(2)
            .map_err(unavailable)?
            .ok_or(StoreError::Unavailable)?,
        description: text(row, 3)?,
        image: text(row, 4)?,
        category: text(row, 5)?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[actix_web::test]
    async fn database_failure_never_falls_back_to_seed_data() {
        let store = CatalogStore::Sql(SqlStore {
            server: "unused.database.windows.net".into(),
            database: "catalog_test".into(),
            client_id: "unused".into(),
            tenant_id: "unused".into(),
            token_file: "nonexistent-catalog-test-token".into(),
            http: reqwest::Client::new(),
            token: Mutex::new(None),
        });
        assert_eq!(store.list().await, Err(StoreError::Unavailable));
        assert_eq!(store.find(1).await, Err(StoreError::Unavailable));
        assert_eq!(store.delete(1).await, Err(StoreError::Unavailable));
        let product = seed_products().remove(0);
        assert_eq!(
            store.insert(product.clone()).await,
            Err(StoreError::Unavailable)
        );
        assert_eq!(store.update(product).await, Err(StoreError::Unavailable));
        let response = crate::routes::error_response(StoreError::Unavailable);
        assert_eq!(
            response.status(),
            actix_web::http::StatusCode::SERVICE_UNAVAILABLE
        );
    }
}
