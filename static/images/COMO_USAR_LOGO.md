# 🎨 Cómo Usar el Logo en NOLIVOS FBA

## 📁 Paso 1: Agrega tu Logo

Coloca tu logo en esta carpeta (`static/images/`) con estos nombres:
- **`logo.png`** o **`logo.svg`** - Logo principal
- **`favicon.ico`** - Para el favicon del navegador

---

## 🖼️ Paso 2: Actualiza los Templates

### En `templates/login.html`:

**Reemplaza esto:**
```html
<div class="logo">
    <h1>🚀 NOLIVOS FBA</h1>
    <p>Amazon Product Research Tool</p>
</div>
```

**Por esto:**
```html
<div class="logo">
    <img src="{{ url_for('static', filename='images/logo.png') }}" 
         alt="NOLIVOS FBA" 
         style="height: 80px; margin-bottom: 1rem;">
    <p>Amazon Product Research Tool</p>
</div>
```

---

### En `templates/users.html` y otras páginas:

**Reemplaza:**
```html
<h1>👥 Gestión de Usuarios</h1>
```

**Por:**
```html
<div style="display: flex; align-items: center; gap: 1rem;">
    <img src="{{ url_for('static', filename='images/logo.png') }}" 
         alt="NOLIVOS FBA" 
         style="height: 40px;">
    <h1>Gestión de Usuarios</h1>
</div>
```

---

### Favicon en TODOS los templates:

Agrega en el `<head>` de cada HTML:

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NOLIVOS FBA</title>
    
    <!-- Favicon -->
    <link rel="icon" type="image/x-icon" 
          href="{{ url_for('static', filename='images/favicon.ico') }}">
    <link rel="icon" type="image/png" sizes="32x32" 
          href="{{ url_for('static', filename='images/favicon-32x32.png') }}">
    <link rel="apple-touch-icon" sizes="180x180" 
          href="{{ url_for('static', filename='images/apple-touch-icon.png') }}">
</head>
```

---

## 🎨 Paso 3: Estilos CSS (Opcional)

Crea `static/css/logo.css`:

```css
.logo-header {
    height: 60px;
    width: auto;
}

.logo-small {
    height: 32px;
    width: auto;
}

.logo-container {
    display: flex;
    align-items: center;
    gap: 1rem;
}

@media (max-width: 768px) {
    .logo-header {
        height: 40px;
    }
}
```

Luego en tus templates:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/logo.css') }}">

<img src="{{ url_for('static', filename='images/logo.png') }}" 
     alt="NOLIVOS FBA" 
     class="logo-header">
```

---

## ✅ Checklist de Implementación

- [ ] Logo agregado como `static/images/logo.png` o `.svg`
- [ ] Favicon agregado como `static/images/favicon.ico`
- [ ] Template `login.html` actualizado con logo
- [ ] Template `users.html` actualizado con logo
- [ ] Favicon agregado en `<head>` de todos los templates
- [ ] CSS opcional creado en `static/css/logo.css`
- [ ] Probado en navegador

---

## 📐 Tamaños Recomendados

- **Logo header:** 60px de alto (máx 300px de ancho)
- **Logo small:** 32-40px de alto
- **Favicon:** 32x32px o 64x64px
- **Apple touch icon:** 180x180px

---

## 💡 Tips

1. **Usa SVG** cuando sea posible (escala perfecto en cualquier tamaño)
2. **Optimiza PNG** con TinyPNG o similar (< 100KB)
3. **Transparencia** - Asegúrate que el logo tiene fondo transparente
4. **Retina** - Proporciona @2x para pantallas de alta resolución

---

¿Necesitas ayuda? Revisa `static/images/README.md`
