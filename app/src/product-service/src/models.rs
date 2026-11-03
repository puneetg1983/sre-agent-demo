use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct Product {
    pub id: i32,
    pub name: String,
    pub price: f32,
    pub description: String,
    pub image: String,
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
}

impl fmt::Display for ValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyName => write!(f, "Product name cannot be empty"),
            Self::EmptyDescription => write!(f, "Product description cannot be empty"),
            Self::EmptyImage => write!(f, "Product image cannot be empty"),
            Self::NegativePrice => write!(f, "Product price cannot be negative"),
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
    if product.price < 0.0 {
        return Err(ValidationError::NegativePrice);
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq)]
pub enum StoreError {
    NotFound(i32),
    Validation(ValidationError),
}

impl fmt::Display for StoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotFound(id) => write!(f, "Product with id {id} not found"),
            Self::Validation(e) => write!(f, "{e}"),
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
    vec![
        Product {
            id: 1,
            name: "Resistance Band Set".into(),
            price: 10.0,
            description: "Three resistance levels for warm-ups, mobility work, and strength training at home or on the go.".into(),
            image: "/resistance-bands.svg".into(),
        },
        Product {
            id: 2,
            name: "Court Pro Tennis Racket".into(),
            price: 89.99,
            description: "A lightweight, pre-strung tennis racket with a comfortable grip for practice sessions and match play.".into(),
            image: "/tennis-racket.svg".into(),
        },
        Product {
            id: 3,
            name: "Tennis Ball Three-Pack".into(),
            price: 8.99,
            description: "Three durable tennis balls for rallies, serving drills, and your next day on the court.".into(),
            image: "/tennis-balls.svg".into(),
        },
        Product {
            id: 4,
            name: "Pickleball Paddle and Ball Set".into(),
            price: 49.99,
            description: "A balanced pickleball paddle with two outdoor balls, ready for social games and skill-building drills.".into(),
            image: "/pickleball-set.svg".into(),
        },
        Product {
            id: 5,
            name: "Table Tennis Starter Set".into(),
            price: 29.99,
            description: "Two table tennis paddles and three balls for quick rallies, family games, and friendly competition.".into(),
            image: "/table-tennis.svg".into(),
        },
        Product {
            id: 6,
            name: "Alpine Ski and Pole Set".into(),
            price: 299.99,
            description: "All-mountain skis with matching poles for winter adventures and confident turns on groomed runs.".into(),
            image: "/alpine-skis.svg".into(),
        },
        Product {
            id: 7,
            name: "Grip Yoga Mat".into(),
            price: 24.99,
            description: "A cushioned, non-slip mat for yoga, stretching, core workouts, and post-training recovery.".into(),
            image: "/yoga-mat.svg".into(),
        },
        Product {
            id: 8,
            name: "Training Dumbbell Pair".into(),
            price: 59.99,
            description: "A pair of comfortable-grip dumbbells for strength circuits, upper-body training, and home workouts.".into(),
            image: "/dumbbells.svg".into(),
        },
        Product {
            id: 9,
            name: "Everyday Running Shoes".into(),
            price: 79.99,
            description: "Lightweight running shoes with cushioned soles for easy runs, gym sessions, and active days.".into(),
            image: "/running-shoes.svg".into(),
        },
        Product {
            id: 10,
            name: "Court and Gym Sports Bag".into(),
            price: 34.99,
            description: "A roomy sports bag with carry handles and a separate shoe compartment for court and gym essentials.".into(),
            image: "/sports-bag.svg".into(),
        },
    ]
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
        }
    }

    #[test]
    fn validate_valid_product() {
        assert!(validate_product(&valid_product()).is_ok());
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
        assert_eq!(store.list().len(), 10);
    }

    #[test]
    fn sports_catalog_preserves_valid_unique_ids_and_images() {
        let products = seed_products();
        let names = products.iter().map(|p| p.name.as_str()).collect::<Vec<_>>().join(" ");
        for sport in ["Tennis", "Pickleball", "Table Tennis", "Ski", "Yoga", "Dumbbell"] {
            assert!(names.contains(sport), "Missing sports category: {sport}");
        }
        for (index, product) in products.iter().enumerate() {
            assert_eq!(product.id, (index + 1) as i32);
            assert!(validate_product(product).is_ok());
            assert!(product.image.ends_with(".svg"));
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
