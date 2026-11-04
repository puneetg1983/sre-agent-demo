use crate::app::AppState;
use crate::models::{Product, ProductPath, StoreError};
use actix_web::{HttpResponse, web};

pub fn error_response(err: StoreError) -> HttpResponse {
    match err {
        StoreError::NotFound(_) => HttpResponse::NotFound().json(err.to_string()),
        StoreError::Validation(_) => HttpResponse::BadRequest().json(err.to_string()),
        StoreError::Unavailable => HttpResponse::ServiceUnavailable().json(err.to_string()),
    }
}

pub async fn get_product(data: web::Data<AppState>, path: web::Path<ProductPath>) -> HttpResponse {
    match data.store.find(path.product_id).await {
        Ok(product) => HttpResponse::Ok().json(product),
        Err(e) => error_response(e),
    }
}

pub async fn get_products(data: web::Data<AppState>) -> HttpResponse {
    match data.store.list().await {
        Ok(products) => HttpResponse::Ok().json(products),
        Err(e) => error_response(e),
    }
}

pub async fn get_metrics(data: web::Data<AppState>) -> HttpResponse {
    match data.store.list().await {
        Ok(products) => HttpResponse::Ok().body(format!(
            "# HELP total_product_count The total number of products in the database\n\
             # TYPE total_product_count gauge\n\
             total_product_count {}\n",
            products.len()
        )),
        Err(e) => error_response(e),
    }
}

pub async fn add_product(data: web::Data<AppState>, body: web::Json<Product>) -> HttpResponse {
    match data.store.insert(body.into_inner()).await {
        Ok(product) => HttpResponse::Ok().json(product),
        Err(e) => error_response(e),
    }
}

pub async fn add_products(
    data: web::Data<AppState>,
    body: web::Json<Vec<Product>>,
) -> HttpResponse {
    // Preserve the existing import contract: ordered inserts, stopping at the first error.
    for product in body.into_inner() {
        if let Err(e) = data.store.insert(product).await {
            return error_response(e);
        }
    }
    HttpResponse::Ok().finish()
}

pub async fn update_product(data: web::Data<AppState>, body: web::Json<Product>) -> HttpResponse {
    match data.store.update(body.into_inner()).await {
        Ok(product) => HttpResponse::Ok().json(product),
        Err(e) => error_response(e),
    }
}

pub async fn delete_product(
    data: web::Data<AppState>,
    path: web::Path<ProductPath>,
) -> HttpResponse {
    match data.store.delete(path.product_id).await {
        Ok(()) => HttpResponse::Ok().body(""),
        Err(e) => error_response(e),
    }
}
