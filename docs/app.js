/* global d3 */
(async function () {
  const { industries } = await (await fetch("data/industries.json")).json();

  const fmtN = d3.format(","), fmtP = d3.format(".1f"), fmtS = d3.format("+.1f"), fmtD = d3.format("$,");
  const $ = (id) => document.getElementById(id);

  const SECTOR_ORDER = ["21","22","23","31-33","42","44-45","48-49","51","52","53","54","56","61","62","71","72","81"];
  const sectorColor = d3.scaleOrdinal()
    .domain(SECTOR_ORDER)
    .range(["#8c6d31","#7b7b7b","#d97706","#c0392b","#e07b39","#f1c40f","#6d4c41","#8e44ad","#1f77b4","#17a2b8","#2e86c1","#5dade2","#27ae60","#16a085","#e91e63","#e67e22","#95a5a6"]);
  const sectorNames = {}; industries.forEach(d => sectorNames[d.sector] = d.sector_name);

  const axisDefs = {
    va_share: { label: "Labor share of value added, 2022 (%)", get: d => d.va_share, domain: [0, 100] },
    cr4: { label: "Share of revenue held by the 4 largest firms (%)", get: d => d.cr4, domain: [0, 100] },
    cr8: { label: "Share of revenue held by the 8 largest firms (%)", get: d => d.cr8, domain: [0, 100] },
    cr20: { label: "Share of revenue held by the 20 largest firms (%)", get: d => d.cr20, domain: [0, 100] },
    cr50: { label: "Share of revenue held by the 50 largest firms (%)", get: d => d.cr50, domain: [0, 100] },
    hhi: { label: "Herfindahl–Hirschman index (50 largest firms)", get: d => d.hhi, log: true },
    cr4_chg: { label: "Change in top-4 revenue share, 2017→2022 (percentage points)", get: d => d.cr4_chg, zero: true },
    payroll_share: { label: "Payroll as % of revenue, 2022", get: d => d.payroll_share },
    payroll_share_chg: { label: "Change in payroll share of revenue, 2017→2022 (points)", get: d => d.payroll_share_chg, zero: true },
    pay_per_emp_k: { label: "Annual payroll per employee, 2022 ($ thousands)", get: d => d.pay_per_emp_k, log: true },
    wage: { label: "Average weekly wage, 2026 Q1 ($)", get: d => d.qcew && d.qcew.avg_wkly_wage, log: true },
    bls_latest: { label: "BLS labor share, latest year (%)", get: d => d.bls && d.bls.values[d.bls.values.length - 1], log: true },
  };
  const sizeDefs = { emp: d => d.emp, revenue_musd: d => d.revenue_musd, firms: d => d.firms, none: () => 1 };
  const colorDefs = {
    cr4_chg: { get: d => d.cr4_chg, label: "Δ CR4 2017→22 (pts)", div: true },
    payroll_share_chg: { get: d => d.payroll_share_chg, label: "Δ payroll share (pts)", div: true, flip: true },
    emp_yoy: { get: d => d.qcew && d.qcew.emp_yoy, label: "Employment growth, yr to 2026 Q1 (%)", div: true, flip: true },
    geo_hhi: { get: d => d.geo && d.geo.geo_hhi, label: "County-level employment HHI", seq: true },
  };

  const svg = d3.select("#chart");
  const m = { t: 18, r: 24, b: 48, l: 58 };
  const gAxes = svg.append("g");
  const gDrift = svg.append("g");
  const gDots = svg.append("g");
  const gFit = svg.append("g");
  const xLab = svg.append("text").attr("class", "axis-label").attr("text-anchor", "middle");
  const yLab = svg.append("text").attr("class", "axis-label").attr("text-anchor", "middle").attr("transform", "rotate(-90)");
  const tip = d3.select("body").append("div").attr("class", "tip").style("display", "none");

  const state = { level: 6, x: "cr4", y: "va_share", size: "emp", color: "sector", off: new Set(), q: "", arrows: false, pinned: null };

  function visible() {
    const rows = industries.filter(d => d.level === state.level && !state.off.has(d.sector));
    const xa = axisDefs[state.x], ya = axisDefs[state.y];
    return rows.filter(d => Number.isFinite(xa.get(d)) && Number.isFinite(ya.get(d)) && (!xa.log || xa.get(d) > 0) && (!ya.log || ya.get(d) > 0));
  }

  function matches(d) {
    if (!state.q) return true;
    const q = state.q.toLowerCase();
    return d.label.toLowerCase().includes(q) || d.code.startsWith(q) || d.sector_name.toLowerCase().includes(q);
  }

  function makeScale(def, values, range) {
    if (def.domain) return d3.scaleLinear().domain(def.domain).range(range).nice();
    const [lo, hi] = d3.extent(values);
    if (def.log) return d3.scaleLog().domain([Math.max(lo * 0.9, 0.1), hi * 1.1]).range(range);
    if (def.zero) {
      const a = d3.quantile(values.map(Math.abs).sort(d3.ascending), 0.98) || Math.max(Math.abs(lo), Math.abs(hi));
      return d3.scaleLinear().domain([-a, a]).range(range).nice().clamp(true);
    }
    return d3.scaleLinear().domain([lo, hi]).range(range).nice();
  }

  function colorScale(rows) {
    if (state.color === "sector") return d => sectorColor(d.sector);
    const def = colorDefs[state.color];
    const vals = rows.map(def.get).filter(Number.isFinite);
    let sc;
    if (def.div) {
      const a = d3.quantile(vals.map(Math.abs).sort(d3.ascending), 0.9) || 1;
      sc = d3.scaleDiverging(def.flip ? t => d3.interpolateRdBu(t) : t => d3.interpolateRdBu(1 - t)).domain([-a, 0, a]).clamp(true);
    } else {
      sc = d3.scaleSequentialLog(d3.interpolateYlOrRd).domain([Math.max(d3.min(vals), 1), d3.max(vals)]).clamp(true);
    }
    return d => { const v = def.get(d); return Number.isFinite(v) ? sc(v) : "#ddd"; };
  }

  function weightedCorr(rows, fx, fy, fw) {
    const pts = rows.map(d => [fx(d), fy(d), fw(d) || 1]).filter(p => p.every(Number.isFinite));
    if (pts.length < 3) return null;
    const W = d3.sum(pts, p => p[2]);
    const mx = d3.sum(pts, p => p[0] * p[2]) / W, my = d3.sum(pts, p => p[1] * p[2]) / W;
    let sxy = 0, sxx = 0, syy = 0;
    for (const [x, y, w] of pts) { sxy += w * (x - mx) * (y - my); sxx += w * (x - mx) ** 2; syy += w * (y - my) ** 2; }
    if (sxx <= 0 || syy <= 0) return null;
    return { r: sxy / Math.sqrt(sxx * syy), slope: sxy / sxx, mx, my, n: pts.length };
  }

  function render() {
    const W = svg.node().clientWidth, H = svg.node().clientHeight;
    const rows = visible();
    const xa = axisDefs[state.x], ya = axisDefs[state.y];
    const x = makeScale(xa, rows.map(xa.get), [m.l, W - m.r]);
    const y = makeScale(ya, rows.map(ya.get), [H - m.b, m.t]);
    const sz = sizeDefs[state.size];
    const r = state.size === "none" ? () => 4.5 : d3.scaleSqrt().domain([0, d3.max(rows, sz) || 1]).range([1.8, state.level <= 3 ? 34 : 22]);
    const col = colorScale(rows);

    gAxes.selectAll("*").remove();
    gAxes.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).ticks(8, xa.log ? "~s" : undefined).tickSize(-(H - m.t - m.b)));
    gAxes.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(8, ya.log ? "~s" : undefined).tickSize(-(W - m.l - m.r)));
    if (xa.zero) gAxes.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", "#999");
    if (ya.zero) gAxes.append("line").attr("y1", y(0)).attr("y2", y(0)).attr("x1", m.l).attr("x2", W - m.r).attr("stroke", "#999");
    xLab.attr("x", (m.l + W - m.r) / 2).attr("y", H - 10).text(xa.label);
    yLab.attr("x", -(m.t + H - m.b) / 2).attr("y", 14).text(ya.label);

    const sorted = rows.slice().sort((a, b) => d3.descending(sz(a) || 0, sz(b) || 0));
    const dots = gDots.selectAll("circle").data(sorted, d => d.code);
    dots.exit().remove();
    dots.enter().append("circle").attr("class", "dot")
      .on("mouseenter", (ev, d) => { showTip(ev, d); if (!state.pinned) showPanel(d); })
      .on("mousemove", (ev) => tip.style("left", (ev.pageX + 12) + "px").style("top", (ev.pageY - 10) + "px"))
      .on("mouseleave", () => { tip.style("display", "none"); if (!state.pinned) showPanel(null); })
      .on("click", (ev, d) => { state.pinned = state.pinned === d ? null : d; showPanel(state.pinned); paint(); })
      .merge(dots)
      .transition().duration(350)
      .attr("cx", d => x(xa.get(d))).attr("cy", d => y(ya.get(d)))
      .attr("r", d => r(sz(d) || 0)).attr("fill", d => col(d));

    // 2017 -> 2022 drift arrows (only meaningful for level metrics that exist in both years)
    gDrift.selectAll("*").remove();
    const canDrift = state.arrows && state.x !== "cr4_chg" && state.y !== "cr4_chg" && state.y !== "payroll_share_chg" && ["cr4"].includes(state.x) && ["payroll_share"].includes(state.y);
    if (canDrift) {
      gDrift.selectAll("line").data(sorted.filter(d => d.cr4_2017 != null && d.payroll_share_2017 > 0 && matches(d))).enter().append("line")
        .attr("class", "drift").attr("stroke", d => col(d))
        .attr("x1", d => x(d.cr4_2017)).attr("y1", d => y(d.payroll_share_2017))
        .attr("x2", d => x(d.cr4)).attr("y2", d => y(d.payroll_share))
        .attr("marker-end", "url(#arrow)");
      if (svg.select("defs").empty()) svg.append("defs").append("marker").attr("id", "arrow").attr("viewBox", "0 0 10 10").attr("refX", 9).attr("refY", 5).attr("markerWidth", 5).attr("markerHeight", 5).attr("orient", "auto").append("path").attr("d", "M0,0L10,5L0,10z").attr("fill", "#555");
    }

    // fit + stats
    gFit.selectAll("*").remove();
    const tx = v => xa.log ? Math.log10(v) : v, ty = v => ya.log ? Math.log10(v) : v;
    const c = weightedCorr(rows, d => tx(xa.get(d)), d => ty(ya.get(d)), d => (state.size === "none" ? 1 : sz(d)));
    if (c) {
      const [x0, x1] = x.domain().map(tx);
      const inv = v => ya.log ? Math.pow(10, v) : v;
      const y0 = inv(c.my + c.slope * (x0 - c.mx)), y1 = inv(c.my + c.slope * (x1 - c.mx));
      gFit.append("line").attr("class", "fit").attr("x1", x.range()[0]).attr("x2", x.range()[1]).attr("y1", y(Math.max(y0, y.domain()[0]))).attr("y2", y(Math.max(y1, y.domain()[0])));
      const w = state.size === "none" ? "unweighted" : `weighted by ${$("size").selectedOptions[0].text.toLowerCase()}`;
      $("stats").innerHTML = `<b>${fmtN(c.n)}</b> industries shown · ${w} correlation${xa.log || ya.log ? " (log axes)" : ""}: <b>r = ${c.r.toFixed(2)}</b>` +
        (state.level >= 4 ? sectorBreakdown(rows, tx, ty, xa, ya, sz) : "");
    } else $("stats").textContent = `${rows.length} industries shown`;

    paint();
    renderLegend(rows);
    $("arrows").disabled = state.y !== "payroll_share";
  }

  function sectorBreakdown(rows, tx, ty, xa, ya, sz) {
    const bySector = d3.groups(rows, d => d.sector).map(([s, g]) => [s, weightedCorr(g, d => tx(xa.get(d)), d => ty(ya.get(d)), d => (state.size === "none" ? 1 : sz(d)))]).filter(([, c]) => c && c.n >= 8);
    bySector.sort((a, b) => d3.ascending(a[1].r, b[1].r));
    if (!bySector.length) return "";
    const f = ([s, c]) => `<span style="color:${sectorColor(s)}">●</span> ${sectorNames[s]} ${c.r.toFixed(2)}`;
    return ` · within-sector: most negative ${f(bySector[0])}; most positive ${f(bySector[bySector.length - 1])}`;
  }

  function paint() {
    gDots.selectAll("circle")
      .classed("dim", d => !matches(d))
      .classed("hit", d => d === state.pinned);
  }

  function renderLegend(rows) {
    const el = $("legend"); el.innerHTML = "";
    if (state.color === "sector") {
      const present = SECTOR_ORDER.filter(s => industries.some(d => d.sector === s && d.level === state.level));
      for (const s of present) {
        const it = document.createElement("span"); it.className = "item" + (state.off.has(s) ? " off" : "");
        it.innerHTML = `<span class="swatch" style="background:${sectorColor(s)}"></span>${sectorNames[s]}`;
        it.onclick = (ev) => {
          if (ev.shiftKey || ev.metaKey) { state.off.has(s) ? state.off.delete(s) : state.off.add(s); }
          else if (state.off.size === present.length - 1 && !state.off.has(s)) state.off.clear();
          else { state.off = new Set(present.filter(p => p !== s)); }
          render();
        };
        el.appendChild(it);
      }
      const hint = document.createElement("span"); hint.className = "item"; hint.style.color = "#999"; hint.textContent = "click a sector to isolate · shift-click to toggle";
      el.appendChild(hint);
    } else {
      const def = colorDefs[state.color];
      const vals = rows.map(def.get).filter(Number.isFinite);
      const it = document.createElement("span"); it.className = "item";
      const grad = def.div ? (def.flip ? "linear-gradient(90deg,#b2182b,#f7f7f7,#2166ac)" : "linear-gradient(90deg,#2166ac,#f7f7f7,#b2182b)") : "linear-gradient(90deg,#ffffcc,#fd8d3c,#800026)";
      const a = def.div ? d3.quantile(vals.map(Math.abs).sort(d3.ascending), 0.9) : null;
      it.innerHTML = `${def.label}: <span>${def.div ? fmtS(-a) : fmtN(Math.round(d3.min(vals)))}</span><span class="ramp" style="background:${grad}"></span><span>${def.div ? fmtS(a) : fmtN(Math.round(d3.max(vals)))}</span>` + (def.div ? " <span style='color:#999'>(red = worse for workers)</span>" : "");
      el.appendChild(it);
    }
  }

  function showTip(ev, d) {
    tip.style("display", "block").html(
      `<b>${d.label}</b> <span class="m">${d.code}</span><br>` +
      `CR4 <b>${fmtP(d.cr4)}%</b>${d.cr4_chg != null ? ` <span class="m">(${fmtS(d.cr4_chg)} since 2017)</span>` : ""}<br>` +
      `Labor share of value added <b>${d.va_share == null ? "n/a" : fmtP(d.va_share) + "%"}</b>${d.va_source === "bea" ? ` <span class="m">(BEA)</span>` : d.va_source === "bea_scaled" ? ` <span class="m">(est., BEA parent)</span>` : ""}<br>` +
      `Payroll share <b>${fmtP(d.payroll_share)}%</b>${d.payroll_share_chg != null ? ` <span class="m">(${fmtS(d.payroll_share_chg)})</span>` : ""}<br>` +
      `<span class="m">${d.emp ? fmtN(d.emp) + " employees · " : ""}${d.firms ? fmtN(d.firms) + " firms" : ""}</span>`);
  }

  function isTrade(d) { return d.sector === "42" || d.sector === "44-45"; }

  function showPanel(d) {
    const el = $("panel");
    if (!d) { el.innerHTML = `<p class="hint">Hover a dot to preview; click to pin it here.</p>`; return; }
    const chg = (v, unit = " pts", flip = false) => v == null ? "" : `<span class="${(flip ? -v : v) > 0 ? "up" : "down"}">${fmtS(v)}${unit}</span>`;
    const q = d.qcew, g = d.geo;
    el.innerHTML = `
      <h2>${d.label}</h2>
      <p class="sub">NAICS ${d.code} · <span style="color:${sectorColor(d.sector)}">●</span> ${d.sector_name}</p>
      <h3>Market structure (Economic Census 2022)</h3>
      <table>
        <tr><td>Top-4 firms' share of revenue</td><td><b>${fmtP(d.cr4)}%</b> ${chg(d.cr4_chg)}</td></tr>
        <tr><td>Top-8 / top-20 / top-50</td><td>${fmtP(d.cr8)} / ${fmtP(d.cr20)} / ${fmtP(d.cr50)}%</td></tr>
        ${d.hhi ? `<tr><td>HHI</td><td>${fmtN(Math.round(d.hhi))}</td></tr>` : ""}
        <tr><td>Firms</td><td>${fmtN(d.firms)}${d.firms_2017 ? ` <span class="${d.firms < d.firms_2017 ? "up" : "down"}">${fmtS(100 * (d.firms / d.firms_2017 - 1))}%</span>` : ""}</td></tr>
        <tr><td>Revenue</td><td>${fmtD(d.revenue_musd)}M</td></tr>
        <tr><td>Revenue per employee</td><td>${fmtD(d.rev_per_emp_k)}k</td></tr>
      </table>
      <h3>Labor's cut</h3>
      <table>
        <tr><td>Labor share of value added, 2022</td><td><b>${d.va_share == null ? "n/a" : fmtP(d.va_share) + "%"}</b> <span class="m">${d.va_source === "census" ? "Census, exact" : d.va_source === "bea_scaled" ? `est. from BEA: ${d.va_bea_industry}${d.va_capped ? " (capped at 100)" : ""}` : ""}</span></td></tr>
        <tr><td>Payroll ÷ revenue, 2022</td><td><b>${fmtP(d.payroll_share)}%</b> ${chg(d.payroll_share_chg, " pts", true)}</td></tr>
        <tr><td>Payroll per employee, 2022</td><td>${fmtD(d.pay_per_emp_k)}k</td></tr>
        <tr><td>Employees (2022)</td><td>${fmtN(d.emp)}</td></tr>
        ${d.top_employers ? `<tr><td>Well-known large employers</td><td>${d.top_employers.join(" · ")}</td></tr>` : ""}
      </table>
      ${d.va_source === "bea_scaled" ? `<p class="note">Estimated: BEA labor share of value added for “${d.va_bea_industry}” (${fmtP(d.va_bea_parent_share)}%) scaled by this industry's payroll ÷ revenue relative to the group's, i.e. it assumes the same intermediate-input share across the group.</p>` : ""}
      ${d.top_employers ? `<p class="note">${d.top_employers_derived ? "Employer names are derived from the curated lists of this group's largest component industries — indicative only." : "Employer names are a curated, indicative list — Census does not disclose which firms make up the top-4 share."}</p>` : ""}
      ${d.bls || d.bea_series ? `<svg class="spark" id="spark"></svg><p class="note">${d.bls ? `Red: ${d.bls.kind}, ${d.bls.years[0]}–${d.bls.years[d.bls.years.length - 1]}${d.bls_code !== d.code ? ` (BLS publishes NAICS ${d.bls_code}, the closest parent)` : ""}.${isTrade(d) ? " BLS output for wholesale/retail is sales margin, not sales." : ""}` : ""}${d.bea_series ? ` Blue: BEA labor share of value added for “${d.va_bea_industry}”, ${d.bea_series.years[0]}–${d.bea_series.years[d.bea_series.years.length - 1]}.` : ""}</p>` : `<p class="note">No labor-share history for this industry.</p>`}
      ${q ? `<h3>Jobs today (QCEW 2026 Q1)</h3>
      <table>
        <tr><td>Employment (March)</td><td>${fmtN(q.emp)} ${chg(q.emp_yoy, "%", true)}</td></tr>
        <tr><td>Establishments</td><td>${fmtN(q.estabs)} ${chg(q.estab_yoy, "%", true)}</td></tr>
        <tr><td>Average weekly wage</td><td>${fmtD(q.avg_wkly_wage)} ${chg(q.wage_yoy, "%", true)}</td></tr>
        ${g ? `<tr><td>Counties with disclosed jobs</td><td>${fmtN(g.counties)}</td></tr>
        <tr><td>Geographic HHI of employment</td><td>${fmtN(g.geo_hhi)}</td></tr>
        <tr><td>Largest county</td><td>${g.top_county} (${fmtP(g.top_county_share)}%)</td></tr>` : ""}
      </table>${g && g.code !== d.code ? `<p class="note">Geography from 4-digit parent ${g.code}; disclosed counties cover ${g.coverage}% of jobs.</p>` : g ? `<p class="note">Disclosed counties cover ${g.coverage}% of national employment.</p>` : ""}` : ""}
      ${d.flag ? `<p class="flag">Census flag ${d.flag}: some values imputed or withheld.</p>` : ""}`;
    if (d.bls || d.bea_series) drawSpark(d.bls, d.bea_series);
  }

  function drawSpark(bls, bea) {
    const s = d3.select("#spark"); const W = s.node().clientWidth, H = 90, mm = { t: 8, r: 6, b: 16, l: 30 };
    const allYears = [...(bls ? bls.years : []), ...(bea ? bea.years : [])];
    const allValues = [...(bls ? bls.values : []), ...(bea ? bea.values : [])].filter(Number.isFinite);
    const x = d3.scaleLinear().domain(d3.extent(allYears)).range([mm.l, W - mm.r]);
    const y = d3.scaleLinear().domain([0, d3.max(allValues) * 1.1]).range([H - mm.b, mm.t]).nice();
    s.append("g").attr("class", "axis").attr("transform", `translate(0,${H - mm.b})`).call(d3.axisBottom(x).ticks(5, "d").tickSize(0));
    s.append("g").attr("class", "axis").attr("transform", `translate(${mm.l},0)`).call(d3.axisLeft(y).ticks(3).tickSize(-(W - mm.l - mm.r)));
    const line = d3.line().defined(p => p[1] != null).x(p => x(p[0])).y(p => y(p[1]));
    if (bls) {
      s.append("path").datum(d3.zip(bls.years, bls.values)).attr("fill", "none").attr("stroke", "#c0392b").attr("stroke-width", 1.6).attr("d", line);
      const last = bls.values[bls.values.length - 1];
      s.append("text").attr("x", W - mm.r).attr("y", y(last) - 4).attr("text-anchor", "end").attr("font-size", 11).attr("fill", "#c0392b").text(fmtP(last) + "%");
    }
    if (bea) {
      s.append("path").datum(d3.zip(bea.years, bea.values)).attr("fill", "none").attr("stroke", "#2b6cb0").attr("stroke-width", 1.6).attr("d", line);
      const last = bea.values[bea.values.length - 1];
      s.append("text").attr("x", W - mm.r).attr("y", y(last) - 4).attr("text-anchor", "end").attr("font-size", 11).attr("fill", "#2b6cb0").text(fmtP(last) + "%");
    }
  }

  for (const id of ["level", "x", "y", "size", "color"]) $(id).onchange = (e) => { state[id] = id === "level" ? +e.target.value : e.target.value; state.pinned = null; showPanel(null); render(); };
  $("search").oninput = (e) => { state.q = e.target.value.trim(); paint(); if (state.arrows) render(); };
  $("arrows").onchange = (e) => { state.arrows = e.target.checked; render(); };
  window.addEventListener("resize", render);
  render();
})();
