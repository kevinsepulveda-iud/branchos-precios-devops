// Buscador de precios: lee datos/catalogo.json (lo genera el pipeline) y filtra en el navegador.
// La misma página funciona en GitHub Pages (JSON estático) y en el contenedor con Flask (JSON en vivo).
"use strict";

const $ = (id) => document.getElementById(id);
const pesos = (v) => (v == null ? "—" : "$ " + v.toLocaleString("es-CO"));
let productos = [];
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function opciones(select, valores) {
  [...new Set(valores)].sort().forEach((v) => select.add(new Option(v, v)));
}

function filtrar() {
  const q = $("f-q").value.trim().toLowerCase();
  const marca = $("f-marca").value;
  const tipo = $("f-tipo").value;
  const max = $("f-max").value ? Number($("f-max").value) : null;
  const orden = $("f-orden").value;
  const lista = productos.filter((p) =>
    (!q || p.nombre.toLowerCase().includes(q)) &&
    (!marca || p.marca === marca) &&
    (!tipo || p.tipo === tipo) &&
    (max === null || p.precio <= max));
  const campos = { descuento: ["descuento_pct", -1], variacion: ["variacion_pct", 1], precio: ["precio", 1], "-precio": ["precio", -1] };
  const [campo, sentido] = campos[orden];
  // los productos nuevos (sin variación) siempre al final
  lista.sort((a, b) => (a[campo] == null) - (b[campo] == null) || sentido * (a[campo] - b[campo]));
  return lista;
}

function cambio(v) {
  if (v == null) return '<span class="nuevo">nuevo</span>';
  if (v === 0) return '<span class="igual">0 %</span>';
  const clase = v < 0 ? "baja" : "sube";
  return `<span class="${clase}">${v > 0 ? "+" : ""}${v.toLocaleString("es-CO")} %</span>`;
}

function pintar() {
  const lista = filtrar();
  $("conteo").textContent = `${lista.length} de ${productos.length} productos`;
  $("filas").innerHTML = lista.slice(0, 300).map((p) => `
    <tr data-sku="${p.sku}">
      <td>${esc(p.nombre)}</td><td>${esc(p.marca)}</td><td>${esc(p.tipo)}</td>
      <td class="num">${pesos(p.precio)}</td><td class="num tachado">${pesos(p.precio_antes)}</td>
      <td class="num">${p.descuento_pct.toLocaleString("es-CO")} %</td><td class="num">${cambio(p.variacion_pct)}</td>
    </tr>`).join("");
  if (lista.length > 300) $("conteo").textContent += " (se muestran los primeros 300; usa los filtros)";
}

function grafico(historial) {
  const svg = $("d-grafico");
  const precios = historial.map((h) => h.precio);
  const min = Math.min(...precios), max = Math.max(...precios);
  const rango = max - min || 1;
  const x = (i) => (historial.length === 1 ? 160 : 30 + (i * 260) / (historial.length - 1));
  const y = (p) => 130 - ((p - min) / rango) * 100;
  const puntos = historial.map((h, i) => `${x(i)},${y(h.precio)}`).join(" ");
  svg.innerHTML = `<polyline points="${puntos}" fill="none" stroke="#1f4e79" stroke-width="2"/>` +
    historial.map((h, i) => `<circle cx="${x(i)}" cy="${y(h.precio)}" r="4" fill="#e07b39"/>
      <text x="${x(i)}" y="152" text-anchor="middle">${h.fecha.slice(5)}</text>`).join("");
}

function detalle(sku) {
  const p = productos.find((x) => x.sku === sku);
  if (!p) return;
  $("d-nombre").textContent = p.nombre;
  $("d-datos").textContent = `${p.marca} · ${p.tipo} · ${p.tallas ?? "?"} tallas disponibles`;
  grafico(p.historial);
  $("d-historial").innerHTML = "<tr><th>Extracción</th><th class='num'>Precio</th></tr>" +
    p.historial.map((h) => `<tr><td>${h.fecha}</td><td class="num">${pesos(h.precio)}</td></tr>`).join("");
  $("d-url").href = p.url;
  $("detalle").hidden = false;
}

async function iniciar() {
  try {
    const r = await fetch("datos/catalogo.json");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const datos = await r.json();
    productos = datos.productos;
    const comparables = productos.filter((p) => p.variacion_pct != null);
    $("k-total").textContent = productos.length;
    $("k-bajaron").textContent = comparables.filter((p) => p.variacion_pct < 0).length;
    $("k-subieron").textContent = comparables.filter((p) => p.variacion_pct > 0).length;
    $("k-nuevos").textContent = productos.length - comparables.length;
    $("fechas").textContent = `extracciones: ${datos.fechas.join(", ")}`;
    $("version").textContent = datos.version;
    opciones($("f-marca"), productos.map((p) => p.marca));
    opciones($("f-tipo"), productos.map((p) => p.tipo));
    pintar();
  } catch (e) {
    $("conteo").textContent = "No se pudo cargar el catálogo (" + e.message + ").";
  }
}

$("filtros").addEventListener("input", pintar);
$("filas").addEventListener("click", (e) => {
  const fila = e.target.closest("tr");
  if (fila) detalle(Number(fila.dataset.sku));
});
$("cerrar").addEventListener("click", () => { $("detalle").hidden = true; });
iniciar();
