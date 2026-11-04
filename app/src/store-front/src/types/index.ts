export interface Product {
  id: number | string
  name: string
  price: number
  description?: string
  image?: string
  category?: string
  [key: string]: string | number | boolean | object | null | undefined
}

export interface CartItem {
  product: Product
  quantity: number
}
