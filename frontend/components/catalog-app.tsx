'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleHelp,
  ImagePlus,
  Menu,
  Moon,
  Search,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Upload,
  X,
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'

type Category = {
  id: string
  name: string
  slug: string
  description: string
  product_count?: number
  created_at: string
}

type ProductImage = {
  id: string
  image: string
  alt_text: string
  position: number
  is_primary: boolean
  created_at: string
}

type Product = {
  id: string
  name: string
  description: string
  category: {
    id: string
    name: string
    slug: string
    description: string
    created_at: string
  } | null
  brand: string
  price: number | string
  currency: string
  country_code: string
  is_active: boolean
  created_at: string
  updated_at: string
  images: ProductImage[]
}

type SearchResult = {
  id: string
  score: number
  product_id: string
  name: string
  description: string
  category: string
  brand: string
  price: number | string
  currency: string
  country_code: string
  is_active: boolean
}

const COUNTRY_LABELS: Record<string, string> = {
  BJ: 'Bénin',
  CI: "Côte d'Ivoire",
  SN: 'Sénégal',
  TG: 'Togo',
  GH: 'Ghana',
  NG: 'Nigeria',
  CM: 'Cameroun',
  BF: 'Burkina Faso',
  ML: 'Mali',
  NE: 'Niger',
  FR: 'France',
}

async function fetchProducts(): Promise<Product[]> {
  console.log('[DEBUG] fetchProducts appelé')
  const res = await fetch(`${API_BASE}/api/catalog/products/`)
  if (!res.ok) throw new Error('Impossible de charger les produits')
  const data = await res.json()
  const products = Array.isArray(data) ? data : data.results ?? []
  console.log('[DEBUG] fetchProducts OK:', products.length, 'produits')
  return products
}

async function fetchCategories(): Promise<Category[]> {
  const res = await fetch(`${API_BASE}/api/catalog/categories/`)
  if (!res.ok) throw new Error('Impossible de charger les catégories')
  const data = await res.json()
  return Array.isArray(data) ? data : data.results ?? []
}

async function fetchProduct(id: string): Promise<Product> {
  const res = await fetch(`${API_BASE}/api/catalog/products/${id}/`)
  if (!res.ok) throw new Error('Produit introuvable')
  return res.json()
}

async function searchText(query: string, k = 10): Promise<SearchResult[]> {
  console.log('[DEBUG] searchText:', query, k)
  const res = await fetch(`${API_BASE}/api/search/text/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k }),
  })
  if (!res.ok) {
    const text = await res.text()
    console.log('[DEBUG] searchText erreur:', res.status, text)
    throw new Error('Erreur de recherche')
  }
  const data = await res.json()
  console.log('[DEBUG] searchText OK:', data.results_count, 'résultats')
  return data.results ?? []
}

async function searchImage(file: File, k = 10): Promise<SearchResult[]> {
  console.log('[DEBUG] searchImage:', file.name, k)
  const form = new FormData()
  form.append('image', file)
  form.append('k', String(k))
  const res = await fetch(`${API_BASE}/api/search/image/`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const text = await res.text()
    console.log('[DEBUG] searchImage erreur:', res.status, text)
    throw new Error('Erreur de recherche par image')
  }
  const data = await res.json()
  console.log('[DEBUG] searchImage OK:', data.results_count, 'résultats')
  return data.results ?? []
}

async function createProduct(payload: {
  name: string
  description: string
  category: string
  brand: string
  price: string
  currency: string
  country_code: string
  is_active: boolean
  image?: File | null
}): Promise<{ ok: boolean; data?: any; error?: string }> {
  const form = new FormData()
  form.append('name', payload.name)
  form.append('description', payload.description)
  form.append('category', payload.category)
  form.append('brand', payload.brand)
  form.append('price', payload.price)
  form.append('currency', payload.currency)
  form.append('country_code', payload.country_code)
  form.append('is_active', payload.is_active ? 'true' : 'false')
  if (payload.image) form.append('image', payload.image)

  const res = await fetch(`${API_BASE}/api/catalog/products/create/`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const text = await res.text()
    return { ok: false, error: text }
  }
  const data = await res.json()
  return { ok: true, data }
}

function formatPrice(value: number | string, currency = 'XOF'): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return value.toString()
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

function countryLabel(code: string): string {
  return COUNTRY_LABELS[code] || code
}

export function CatalogApp() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [activePage, setActivePage] = useState<'search' | 'create' | 'detail'>('search')
  const [selected, setSelected] = useState<Product | null>(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [searchMode, setSearchMode] = useState<'text' | 'image'>('text')
  const [submitted, setSubmitted] = useState(false)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [products, setProducts] = useState<Product[]>([])
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [activeCountry, setActiveCountry] = useState<string>('all')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const [prods, cats] = await Promise.all([fetchProducts(), fetchCategories()])
        if (!cancelled) {
          setProducts(prods)
          setCategories(cats)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Erreur inconnue')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const handleTextSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setActiveCategory('all')
    setActiveCountry('all')
    try {
      const results = await searchText(query, 10)
      setSearchResults(results)
      setActivePage('search')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de recherche')
    } finally {
      setLoading(false)
    }
  }, [query])

  const handleImageSearch = useCallback(async (file: File) => {
    setLoading(true)
    setError(null)
    try {
      const results = await searchImage(file, 10)
      setSearchResults(results)
      setActivePage('search')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de recherche par image')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleCreate = useCallback(async (formData: FormData) => {
    setLoading(true)
    setError(null)
    try {
      const result = await createProduct({
        name: formData.get('name') as string,
        description: formData.get('description') as string,
        category: formData.get('category') as string,
        brand: formData.get('brand') as string,
        price: formData.get('price') as string,
        currency: formData.get('currency') as string,
        country_code: formData.get('country_code') as string,
        is_active: formData.get('is_active') === 'true',
        image: formData.get('image') as File | null,
      })
      if (!result.ok) {
        setError(result.error || 'Erreur lors de la création')
        return
      }
      setSubmitted(true)
      setActivePage('search')
      // Recharger les produits pour voir le nouveau
      const prods = await fetchProducts()
      setProducts(prods)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue')
    } finally {
      setLoading(false)
    }
  }, [])

  const viewProduct = useCallback((id: string) => {
    setLoading(true)
    fetchProduct(id)
      .then((p) => {
        setSelected(p)
        setActivePage('detail')
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Erreur chargement produit'))
      .finally(() => setLoading(false))
  }, [])

  const filteredProducts = useMemo(() => {
    if (searchResults.length > 0) return searchResults as Product[]
    return products.filter((p) => {
      if (activeCategory !== 'all' && p.category?.slug !== activeCategory) return false
      if (activeCountry !== 'all' && p.country_code !== activeCountry) return false
      return true
    })
  }, [products, searchResults, activeCategory, activeCountry])

  const renderSearchItem = (item: Product | SearchResult) => {
    const isSearchResult = 'product_id' in item

    // Construire l'URL de l'image : pour les résultats ES, pas d'images disponibles
    let imageUrl: string
    if (!isSearchResult && 'images' in item && item.images.length > 0 && item.images[0].image) {
      imageUrl = item.images[0].image.startsWith('http')
        ? item.images[0].image
        : `${API_BASE}${item.images[0].image}`
    } else {
      // Fallback : image par couleur selon la catégorie
      const hue = Math.abs(item.name.split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % 360
      imageUrl = `https://placehold.co/300x300/${hue.toString(16).padStart(2, '0')}af8d/ffffff?text=${encodeURIComponent(item.name.slice(0, 1))}`
    }

    const categoryDisplay = isSearchResult
      ? item.category
      : item.category?.name ?? 'Non classée'

    return (
      <button
        key={item.id}
        className="product-card"
        onClick={() => {
          if (isSearchResult) {
            viewProduct(item.product_id)
          } else {
            setSelected(item)
            setActivePage('detail')
          }
        }}
      >
        <div className="product-image">
          <img src={imageUrl} alt={item.name} loading="lazy" />
          {item.score !== undefined && <span className="score">{Math.round(item.score * 100)}% match</span>}
        </div>
        <div className="product-info">
          <div>
            <span>{categoryDisplay}</span>
            <h3>{item.name}</h3>
          </div>
          <strong>{formatPrice(item.price, item.currency)}</strong>
        </div>
        <div className="product-origin">
          {countryLabel(item.country_code)}
        </div>
      </button>
    )
  }

  return (
    <div className={theme === 'dark' ? 'app-shell dark' : 'app-shell'}>
      <header className="site-header">
        <button className="brand" onClick={() => { setActivePage('search'); setSelected(null); setSearchResults([]) }} aria-label="Retour à l'accueil">
          <span className="brand-mark" aria-hidden="true">M</span>
        </button>
        <nav className={mobileNav ? 'main-nav is-open' : 'main-nav'} aria-label="Navigation principale">
          <button className={activePage === 'search' && !selected ? 'nav-link active' : 'nav-link'} onClick={() => { setActivePage('search'); setSelected(null); setSearchResults([]); setMobileNav(false) }}>Explorer</button>
          <button className={activePage === 'create' ? 'nav-link active' : 'nav-link'} onClick={() => { setActivePage('create'); setSelected(null); setMobileNav(false) }}>Créer un produit</button>
        </nav>
        <div className="header-actions">
          {error && <span className="error-badge" title={error}>⚠️</span>}
          <button className="icon-button" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} aria-label={`Activer le mode ${theme === 'light' ? 'sombre' : 'clair'}`}>{theme === 'light' ? <Moon /> : <Sun />}</button>
          <button className="icon-button mobile-menu" onClick={() => setMobileNav(!mobileNav)} aria-label="Ouvrir le menu"><Menu /></button>
          <span className="avatar">AN</span>
        </div>
      </header>

      <main>
        {loading && <div className="loading">Chargement...</div>}
        {error && !loading && <div className="error-banner">{error}<button onClick={() => setError(null)}>X</button></div>}

        {selected ? (
          <ProductDetail product={selected} onBack={() => setSelected(null)} />
        ) : activePage === 'create' ? (
          <CreateProduct onSubmit={handleCreate} categories={categories} />
        ) : (
          <>
            <section className="hero-section">
              <div className="eyebrow"><Sparkles /> CATALOGUE INTELLIGENT</div>
              <h1>Trouvez ce qui<br /><em>vous ressemble.</em></h1>
              <p>Explorez une sélection de produits africains grâce à une recherche simple, textuelle ou visuelle.</p>
              <div className="search-panel">
                <div className="search-tabs">
                  <button className={searchMode === 'text' ? 'tab active' : 'tab'} onClick={() => setSearchMode('text')}>
                    <Search /> Recherche textuelle
                  </button>
                  <button className={searchMode === 'image' ? 'tab active' : 'tab'} onClick={() => setSearchMode('image')}>
                    <ImagePlus /> Recherche par image
                  </button>
                </div>
                {searchMode === 'text' ? (
                  <form onSubmit={handleTextSearch} className="search-row">
                    <Search className="search-icon" />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Je cherche une tenue pour cérémonie…"
                    />
                    <button className="primary-button" type="submit">
                      Rechercher <ArrowUpRight />
                    </button>
                  </form>
                ) : (
                  <label className="dropzone" onDrop={async (e) => {
                    e.preventDefault()
                    const file = e.dataTransfer.files[0]
                    if (file) await handleImageSearch(file)
                  }} onDragOver={(e) => e.preventDefault()}>
                    <Upload />
                    <span><b>Déposez une image</b> ou cliquez pour parcourir</span>
                    <input type="file" accept="image/*" onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (file) handleImageSearch(file)
                    }} />
                  </label>
                )}
              </div>
            </section>

            <section className="results-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">CATALOGUE</span>
                  <h2>{query ? 'Résultats de votre recherche' : 'Votre sélection apparaîtra ici'}</h2>
                </div>
                <button className="filter-button"><SlidersHorizontal /> Filtres <span>3</span></button>
              </div>
              <div className="filter-row">
                <button
                  className={`filter-chip ${activeCategory === 'all' ? 'selected' : ''}`}
                  onClick={() => setActiveCategory('all')}
                >
                  Tous les produits <ChevronDown />
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat.slug}
                    className={`filter-chip ${activeCategory === cat.slug ? 'selected' : ''}`}
                    onClick={() => setActiveCategory(cat.slug)}
                  >
                    {cat.name} <ChevronDown />
                  </button>
                ))}
                {COUNTRY_LABELS[activeCountry] && activeCountry !== 'all' ? (
                  <button
                    className="filter-chip selected"
                    onClick={() => setActiveCountry('all')}
                  >
                    {COUNTRY_LABELS[activeCountry]} <ChevronDown />
                  </button>
                ) : (
                  <button
                    className="filter-chip"
                    onClick={() => {
                      // Cycle rapide : pour la démo, on affiche BJ
                      setActiveCountry('BJ')
                    }}
                  >
                    Pays d’origine <ChevronDown />
                  </button>
                )}
                <button className="filter-chip">Prix <ChevronDown /></button>
              </div>
              <div className="result-meta">
                <span>{filteredProducts.length} produits trouvés</span>
                <button>Trier par pertinence <ChevronDown /></button>
              </div>
              {filteredProducts.length ? (
                <div className="product-grid">
                  {filteredProducts.map((p) => renderSearchItem(p))}
                </div>
              ) : (
                <div className="empty-state">
                  <Search />
                  <h3>Aucun résultat pour cette recherche</h3>
                  <p>Essayez avec d’autres mots-clés ou explorez toute la sélection.</p>
                  <button className="secondary-button" onClick={() => { setQuery(''); setSearchResults([]) }}>Réinitialiser</button>
                </div>
              )}
            </section>
          </>
        )}
      </main>
      <footer>
        <span>© 2026</span>
        <span>Recherche sémantique · API Django</span>
        <button aria-label="Aide"><CircleHelp /></button>
      </footer>
    </div>
  )
}

function ProductCard({ product, onClick }: { product: Product; onClick: () => void }) {
  const imageUrl = product.images.length > 0 && product.images[0].image
    ? product.images[0].image.startsWith('http')
      ? product.images[0].image
      : `${API_BASE}${product.images[0].image}`
    : '/placeholder.svg'

  return (
    <button className="product-card" onClick={onClick}>
      <div className="product-image">
        <img src={imageUrl} alt={product.name} loading="lazy" />
      </div>
      <div className="product-info">
        <div>
          <span>{product.category?.name ?? 'Non classée'}</span>
          <h3>{product.name}</h3>
        </div>
        <strong>{formatPrice(product.price, product.currency)}</strong>
      </div>
      <div className="product-origin">
        {countryLabel(product.country_code)}
      </div>
    </button>
  )
}

function ProductDetail({ product, onBack }: { product: Product; onBack: () => void }) {
  const primaryImage = product.images.find((img) => img.is_primary) ?? product.images[0]
  const imageUrl = primaryImage?.image
    ? primaryImage.image.startsWith('http')
      ? primaryImage.image
      : `${API_BASE}${primaryImage.image}`
    : '/placeholder.svg'

  return (
    <section className="detail-page">
      <button className="back-link" onClick={onBack}><ArrowLeft /> Retour aux résultats</button>
      <div className="detail-grid">
        <div className="detail-image">
          <img src={imageUrl} alt={product.name} />
          {product.images.slice(1).map((img) => (
            <img key={img.id} src={`${API_BASE}${img.image}`} alt={img.alt_text || product.name} className="thumb" />
          ))}
        </div>
        <div className="detail-copy">
          <span className="eyebrow">{product.category?.name ?? 'Non classée'}</span>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price, product.currency)}</p>
          <p>{product.description}</p>
          <div className="detail-list">
            <div><span>Pays d’origine</span><b>{countryLabel(product.country_code)}</b></div>
            <div><span>Marque</span><b>{product.brand || '—'}</b></div>
            <div><span>Disponibilité</span><b>{product.is_active ? 'En stock' : 'Inactif'}</b></div>
            <div><span>Créé le</span><b>{new Date(product.created_at).toLocaleDateString('fr-FR')}</b></div>
          </div>
          <button className="primary-button">Contacter le vendeur <ArrowUpRight /></button>
        </div>
      </div>
    </section>
  )
}

function CreateProduct({
  onSubmit,
  categories,
}: {
  onSubmit: (formData: FormData) => void
  categories: Category[]
}) {
  const [form, setForm] = useState({
    name: '',
    description: '',
    category: '',
    brand: '',
    price: '',
    currency: 'XOF',
    country_code: 'BJ',
    is_active: true,
    image: null as File | null,
  })

  const handleChange = (e: React.ChangeEvent) => {
    const { name, value, type, checked, files } = e.target
    if (type === 'checkbox') {
      setForm((prev) => ({ ...prev, [name]: checked }))
    } else if (files && files.length) {
      setForm((prev) => ({ ...prev, [name]: files[0] }))
    } else {
      setForm((prev) => ({ ...prev, [name]: value }))
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const formData = new FormData()
    formData.append('name', form.name)
    formData.append('description', form.description)
    formData.append('category', form.category)
    formData.append('brand', form.brand)
    formData.append('price', form.price)
    formData.append('currency', form.currency)
    formData.append('country_code', form.country_code)
    formData.append('is_active', form.is_active ? 'true' : 'false')
    if (form.image) formData.append('image', form.image)
    onSubmit(formData)
  }

  return (
    <section className="create-page">
      <div className="create-intro">
        <span className="eyebrow">NOUVELLE FICHE</span>
        <h1>Ajouter un produit<br /><em>au catalogue.</em></h1>
        <p>Créez une fiche claire et complète. L’indexation sémantique se fera automatiquement à la publication.</p>
      </div>
      <form className="product-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            Nom du produit
            <input name="name" required placeholder="Ex. Boubou N°04" value={form.name} onChange={handleChange} />
          </label>
          <label>
            Marque
            <input name="brand" placeholder="Ex. Atelier Sira" value={form.brand} onChange={handleChange} />
          </label>
        </div>
        <label>
          Description
          <textarea name="description" required placeholder="Décrivez le produit, ses matières, son histoire…" rows={4} value={form.description} onChange={handleChange} />
        </label>
        <div className="form-row">
          <label>
            Catégorie
            <select name="category" required value={form.category} onChange={handleChange}>
              <option value="" disabled>Sélectionner</option>
              {categories.map((cat) => (
                <option key={cat.slug} value={cat.slug}>{cat.name}</option>
              ))}
            </select>
          </label>
          <label>
            Pays d’origine
            <select name="country_code" required value={form.country_code} onChange={handleChange}>
              <option value="BJ">BJ — Bénin</option>
              <option value="CI">CI — Côte d’Ivoire</option>
              <option value="SN">SN — Sénégal</option>
              <option value="TG">TG — Togo</option>
              <option value="GH">GH — Ghana</option>
              <option value="NG">NG — Nigeria</option>
              <option value="CM">CM — Cameroun</option>
              <option value="BF">BF — Burkina Faso</option>
              <option value="ML">ML — Mali</option>
              <option value="NE">NE — Niger</option>
              <option value="FR">FR — France</option>
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            Prix
            <input name="price" type="number" step="0.01" placeholder="0" required value={form.price} onChange={handleChange} />
          </label>
          <label>
            Devise
            <select name="currency" required value={form.currency} onChange={handleChange}>
              <option value="XOF">XOF</option>
              <option value="EUR">EUR</option>
            </select>
          </label>
        </div>
        <label className="upload-field">
          <ImagePlus />
          <span>
            <b>Ajouter une image</b>
            <small>PNG, JPG jusqu’à 10 Mo</small>
          </span>
          <input type="file" accept="image/*" name="image" onChange={handleChange} />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={submitted}>
            Publier le produit <ArrowUpRight />
          </button>
        </div>
        {submitted && <div className="success"><Check /> Produit créé et indexé avec succès.</div>}
      </form>
    </section>
  )
}
