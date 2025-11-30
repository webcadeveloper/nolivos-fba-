# 📁 Carpeta de Imágenes

## 🎨 Logo de NOLIVOS FBA

Coloca tu logo aquí con estos nombres:

### Logos Principales:
- **`logo.png`** - Logo principal (PNG con transparencia)
- **`logo.svg`** - Logo vectorial (SVG, recomendado)
- **`logo-white.png`** - Logo en blanco (para fondos oscuros)

### Favicon:
- **`favicon.ico`** - 32x32px o 64x64px
- **`favicon-16x16.png`** - 16x16px
- **`favicon-32x32.png`** - 32x32px
- **`apple-touch-icon.png`** - 180x180px (para iOS)

### Tamaños Recomendados:

#### Logo Principal:
- **Ancho:** 200-300px
- **Alto:** 50-80px
- **Formato:** PNG con transparencia o SVG
- **Peso:** < 100KB

#### Logo Cuadrado (para redes sociales):
- **`logo-square.png`** - 512x512px
- **Formato:** PNG
- **Peso:** < 200KB

---

## 🖼️ Otras Imágenes

Puedes agregar:
- **`hero-bg.jpg`** - Background del hero section
- **`og-image.png`** - 1200x630px (Open Graph para redes sociales)
- **`placeholder.png`** - Imagen placeholder

---

## 💡 Cómo Usar en Templates

```html
<!-- Logo principal -->
<img src="{{ url_for('static', filename='images/logo.png') }}" 
     alt="NOLIVOS FBA Logo" 
     style="height: 60px;">

<!-- Logo SVG (recomendado) -->
<img src="{{ url_for('static', filename='images/logo.svg') }}" 
     alt="NOLIVOS FBA Logo" 
     class="logo">

<!-- Favicon en <head> -->
<link rel="icon" type="image/x-icon" 
      href="{{ url_for('static', filename='images/favicon.ico') }}">
```

---

## 📐 Especificaciones Técnicas

### Logo Principal:
- **Colores:** RGB para web
- **Background:** Transparente
- **Resolución:** @2x para Retina (doble tamaño)

### Formato Óptimo:
1. **SVG** - Mejor opción (escalable, ligero)
2. **PNG** - Segunda opción (con transparencia)
3. **WebP** - Alternativa moderna (menor peso)

---

## ✅ Checklist

- [ ] `logo.png` - Logo principal añadido
- [ ] `logo.svg` - Logo vectorial (opcional pero recomendado)
- [ ] `favicon.ico` - Favicon añadido
- [ ] Logo optimizado (< 100KB)
- [ ] Templates actualizados con rutas correctas

---

**Nota:** Después de agregar el logo, actualiza los templates en `templates/` para usarlo.
