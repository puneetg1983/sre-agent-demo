use product_service::{
    models::{Product, StoreError},
    store::CatalogStore,
};

// Provision a separate *_test database and workload-identity catalog grants first.
// Never point mutation tests at the business database.
#[actix_web::test]
#[ignore = "requires an isolated Azure SQL *_test database and federated identity"]
async fn sql_crud_persists_between_store_instances() {
    assert!(std::env::var("SQL_DATABASE").unwrap().ends_with("_test"));
    let store = CatalogStore::sql().unwrap();
    let product = store
        .insert(Product {
            id: 0,
            name: "SQL integration fixture".into(),
            price: 12.5,
            description: "Isolated persistence test".into(),
            image: "/test.svg".into(),
            category: "Training".into(),
        })
        .await
        .unwrap();
    let second = CatalogStore::sql().unwrap();
    assert_eq!(second.find(product.id).await.unwrap(), product);
    let mut updated = product.clone();
    updated.category = "Outdoor".into();
    updated.price = 15.0;
    assert_eq!(store.update(updated.clone()).await.unwrap(), updated);
    assert_eq!(second.find(product.id).await.unwrap().category, "Outdoor");
    assert!(
        second
            .list()
            .await
            .unwrap()
            .iter()
            .any(|p| p.id == product.id)
    );
    second.delete(product.id).await.unwrap();
    assert_eq!(
        store.find(product.id).await,
        Err(StoreError::NotFound(product.id))
    );
    assert_eq!(
        store.delete(product.id).await,
        Err(StoreError::NotFound(product.id))
    );
}
