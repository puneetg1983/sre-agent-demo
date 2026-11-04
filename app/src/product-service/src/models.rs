use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct Product {
    pub id: i32,
    pub name: String,
    pub price: f32,
    pub description: String,
    pub image: String,
    #[serde(default = "default_category")]
    pub category: String,
}

fn default_category() -> String {
    "General".into()
}

#[derive(Deserialize)]
pub struct ProductPath {
    pub product_id: i32,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ValidationError {
    EmptyName,
    EmptyDescription,
    EmptyImage,
    NegativePrice,
    InvalidCategory,
    FieldTooLong,
}

impl fmt::Display for ValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyName => write!(f, "Product name cannot be empty"),
            Self::EmptyDescription => write!(f, "Product description cannot be empty"),
            Self::EmptyImage => write!(f, "Product image cannot be empty"),
            Self::NegativePrice => write!(f, "Product price cannot be negative"),
            Self::InvalidCategory => write!(f, "Product category cannot be empty"),
            Self::FieldTooLong => write!(f, "Product field exceeds the maximum length"),
        }
    }
}

pub fn validate_product(product: &Product) -> Result<(), ValidationError> {
    if product.name.trim().is_empty() {
        return Err(ValidationError::EmptyName);
    }
    if product.description.trim().is_empty() {
        return Err(ValidationError::EmptyDescription);
    }
    if product.image.trim().is_empty() {
        return Err(ValidationError::EmptyImage);
    }
    if !product.price.is_finite() || product.price < 0.0 {
        return Err(ValidationError::NegativePrice);
    }
    if product.category.trim().is_empty() {
        return Err(ValidationError::InvalidCategory);
    }
    if product.name.encode_utf16().count() > 200
        || product.description.encode_utf16().count() > 4000
        || product.image.encode_utf16().count() > 2048
        || product.category.encode_utf16().count() > 100
    {
        return Err(ValidationError::FieldTooLong);
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq)]
pub enum StoreError {
    NotFound(i32),
    Validation(ValidationError),
    Unavailable,
}

impl fmt::Display for StoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotFound(id) => write!(f, "Product with id {id} not found"),
            Self::Validation(e) => write!(f, "{e}"),
            Self::Unavailable => write!(f, "Product catalog is temporarily unavailable"),
        }
    }
}

impl From<ValidationError> for StoreError {
    fn from(e: ValidationError) -> Self {
        Self::Validation(e)
    }
}

pub struct ProductStore {
    products: Vec<Product>,
    next_id: i32,
}

impl ProductStore {
    pub fn new(products: Vec<Product>) -> Self {
        let next_id = products.iter().map(|p| p.id).max().unwrap_or(0) + 1;
        Self { products, next_id }
    }

    pub fn list(&self) -> &[Product] {
        &self.products
    }

    pub fn find(&self, id: i32) -> Result<&Product, StoreError> {
        self.products
            .iter()
            .find(|p| p.id == id)
            .ok_or(StoreError::NotFound(id))
    }

    pub fn insert(&mut self, mut product: Product) -> Result<Product, StoreError> {
        validate_product(&product)?;
        product.id = self.next_id;
        self.next_id += 1;
        self.products.push(product.clone());
        Ok(product)
    }

    pub fn update(&mut self, product: Product) -> Result<Product, StoreError> {
        validate_product(&product)?;
        let index = self
            .products
            .iter()
            .position(|p| p.id == product.id)
            .ok_or(StoreError::NotFound(product.id))?;
        self.products[index] = product.clone();
        Ok(product)
    }

    pub fn delete(&mut self, id: i32) -> Result<(), StoreError> {
        let index = self
            .products
            .iter()
            .position(|p| p.id == id)
            .ok_or(StoreError::NotFound(id))?;
        self.products.remove(index);
        Ok(())
    }

    pub fn count(&self) -> usize {
        self.products.len()
    }
}

pub fn seed_products() -> Vec<Product> {
    serde_json::from_str(include_str!("../catalog.json"))
        .expect("Canonical catalog must be valid JSON")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_product() -> Product {
        Product {
            id: 0,
            name: "Test Product".into(),
            price: 9.99,
            description: "A test product".into(),
            image: "/test.jpg".into(),
            category: "General".into(),
        }
    }

    #[test]
    fn validate_valid_product() {
        assert!(validate_product(&valid_product()).is_ok());
    }

    #[test]
    fn legacy_clients_default_to_general() {
        let mut value = serde_json::to_value(valid_product()).unwrap();
        value.as_object_mut().unwrap().remove("category");
        let product: Product = serde_json::from_value(value).unwrap();
        assert_eq!(product.category, "General");
    }

    #[test]
    fn validate_category_and_sql_limits() {
        let mut product = valid_product();
        product.category = "   ".into();
        assert_eq!(
            validate_product(&product),
            Err(ValidationError::InvalidCategory)
        );
        product.category = "x".repeat(101);
        assert_eq!(
            validate_product(&product),
            Err(ValidationError::FieldTooLong)
        );
        product = valid_product();
        product.price = f32::NAN;
        assert_eq!(
            validate_product(&product),
            Err(ValidationError::NegativePrice)
        );
    }

    #[test]
    fn validate_empty_name() {
        let mut p = valid_product();
        p.name = "".into();
        assert_eq!(validate_product(&p), Err(ValidationError::EmptyName));
    }

    #[test]
    fn validate_whitespace_name() {
        let mut p = valid_product();
        p.name = "   ".into();
        assert_eq!(validate_product(&p), Err(ValidationError::EmptyName));
    }

    #[test]
    fn validate_empty_description() {
        let mut p = valid_product();
        p.description = "".into();
        assert_eq!(validate_product(&p), Err(ValidationError::EmptyDescription));
    }

    #[test]
    fn validate_empty_image() {
        let mut p = valid_product();
        p.image = "".into();
        assert_eq!(validate_product(&p), Err(ValidationError::EmptyImage));
    }

    #[test]
    fn validate_negative_price() {
        let mut p = valid_product();
        p.price = -1.0;
        assert_eq!(validate_product(&p), Err(ValidationError::NegativePrice));
    }

    #[test]
    fn validate_zero_price_ok() {
        let mut p = valid_product();
        p.price = 0.0;
        assert!(validate_product(&p).is_ok());
    }

    #[test]
    fn store_insert_assigns_id() {
        let mut store = ProductStore::new(vec![]);
        let p = store.insert(valid_product()).unwrap();
        assert_eq!(p.id, 1);

        let p2 = store.insert(valid_product()).unwrap();
        assert_eq!(p2.id, 2);
    }

    #[test]
    fn store_insert_rejects_invalid() {
        let mut store = ProductStore::new(vec![]);
        let mut p = valid_product();
        p.name = "".into();
        assert!(store.insert(p).is_err());
        assert_eq!(store.count(), 0);
    }

    #[test]
    fn store_find_existing() {
        let store = ProductStore::new(seed_products());
        let p = store.find(1).unwrap();
        assert_eq!(p.name, "Resistance Band Set");
    }

    #[test]
    fn store_find_missing() {
        let store = ProductStore::new(seed_products());
        assert_eq!(store.find(999), Err(StoreError::NotFound(999)));
    }

    #[test]
    fn store_update_existing() {
        let mut store = ProductStore::new(seed_products());
        let mut p = store.find(1).unwrap().clone();
        p.name = "Updated Name".into();
        let updated = store.update(p).unwrap();
        assert_eq!(updated.name, "Updated Name");
        assert_eq!(store.find(1).unwrap().name, "Updated Name");
    }

    #[test]
    fn store_update_missing() {
        let mut store = ProductStore::new(seed_products());
        let mut p = valid_product();
        p.id = 999;
        assert_eq!(store.update(p), Err(StoreError::NotFound(999)));
    }

    #[test]
    fn store_update_rejects_invalid() {
        let mut store = ProductStore::new(seed_products());
        let mut p = store.find(1).unwrap().clone();
        p.price = -5.0;
        assert!(store.update(p).is_err());
    }

    #[test]
    fn store_delete_existing() {
        let mut store = ProductStore::new(seed_products());
        let initial_count = store.count();
        store.delete(1).unwrap();
        assert_eq!(store.count(), initial_count - 1);
        assert!(store.find(1).is_err());
    }

    #[test]
    fn store_delete_missing() {
        let mut store = ProductStore::new(seed_products());
        assert_eq!(store.delete(999), Err(StoreError::NotFound(999)));
    }

    #[test]
    fn store_list_returns_all() {
        let store = ProductStore::new(seed_products());
        assert_eq!(store.list().len(), 210);
    }

    #[test]
    fn sports_catalog_preserves_valid_unique_ids_and_images() {
        let products = seed_products();
        assert_eq!(products.len(), 210);
        assert_eq!(
            products
                .iter()
                .map(|p| &p.image)
                .collect::<std::collections::HashSet<_>>()
                .len(),
            210
        );
        let names = products
            .iter()
            .map(|p| p.name.as_str())
            .collect::<Vec<_>>()
            .join(" ");
        for sport in [
            "Tennis",
            "Pickleball",
            "Table Tennis",
            "Ski",
            "Yoga",
            "Dumbbell",
        ] {
            assert!(names.contains(sport), "Missing sports category: {sport}");
        }
        for (index, product) in products.iter().enumerate() {
            assert_eq!(product.id, (index + 1) as i32);
            assert!(validate_product(product).is_ok());
            if index < 10 {
                assert!(product.image.ends_with(".svg"));
            } else {
                assert_eq!(
                    product.image,
                    format!("/products/product-{:04}.jpg", product.id)
                );
            }
        }
        assert_eq!(products[0].price, 10.0);
    }

    #[test]
    fn store_ids_never_reused_after_delete() {
        let mut store = ProductStore::new(vec![]);
        let p1 = store.insert(valid_product()).unwrap();
        let p2 = store.insert(valid_product()).unwrap();
        store.delete(p1.id).unwrap();
        let p3 = store.insert(valid_product()).unwrap();
        assert_eq!(p3.id, 3);
        assert_ne!(p3.id, p1.id);
        assert_ne!(p3.id, p2.id);
    }
}
