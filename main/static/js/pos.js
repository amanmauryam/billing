(function () {
  "use strict";

  var app = document.getElementById("pos-app");
  if (!app) return;

  var searchUrl = app.dataset.searchUrl;
  var lookupUrl = app.dataset.lookupUrl;
  var checkoutUrl = app.dataset.checkoutUrl;
  var pricingMode = app.dataset.pricingMode;

  var scanInput = document.getElementById("scan-input");
  var scanButton = document.getElementById("scan-button");
  var feedback = document.getElementById("scan-feedback");
  var resultsEl = document.getElementById("results");
  var cartEl = document.getElementById("cart");
  var cartCount = document.getElementById("cart-count");
  var clearButton = document.getElementById("clear-cart");
  var checkoutButton = document.getElementById("checkout-button");
  var checkoutLabel = document.getElementById("checkout-label");
  var checkoutError = document.getElementById("checkout-error");
  var paymentSelect = document.getElementById("payment-method");
  var subtotalEl = document.getElementById("total-subtotal");
  var taxEl = document.getElementById("total-tax");
  var grandEl = document.getElementById("total-grand");
  var successPanel = document.getElementById("success-panel");
  var successBill = document.getElementById("success-bill");
  var viewReceipt = document.getElementById("view-receipt");
  var printReceipt = document.getElementById("print-receipt");
  var newBillButton = document.getElementById("new-bill");

  var ICON = {
    minus:
      '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>',
    plus:
      '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5v14"/></svg>',
    x: '<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  };

  var cart = [];
  var pendingToken = null;
  var inFlight = false;

  function getCsrfToken() {
    var match = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[2]) : "";
  }

  function formatMoney(value) {
    try {
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
      }).format(value);
    } catch (e) {
      return "₹" + Number(value).toFixed(2);
    }
  }

  function round2(value) {
    return Math.round((value + Number.EPSILON) * 100) / 100;
  }

  function showFeedback(message, kind) {
    feedback.textContent = message || "";
    feedback.className = "mt-2 text-[13px] min-h-[1.25rem]";
    if (kind === "error") feedback.classList.add("text-danger");
    else if (kind === "success") feedback.classList.add("text-success");
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text == null ? "" : text;
    return div.innerHTML;
  }

  function findLine(productId) {
    for (var i = 0; i < cart.length; i++) {
      if (cart[i].id === productId) return cart[i];
    }
    return null;
  }

  function lineAmount(line) {
    var raw = round2(line.price * line.quantity);
    if (pricingMode === "inclusive") {
      var divisor = 1 + line.gst_rate / 100;
      var taxable = divisor === 0 ? raw : raw / divisor;
      return { raw: raw, tax: round2(raw - round2(taxable)), total: raw };
    }
    var tax = round2((raw * line.gst_rate) / 100);
    return { raw: raw, tax: tax, total: round2(raw + tax) };
  }

  function recalc() {
    var subtotal = 0;
    var tax = 0;
    var grand = 0;
    var count = 0;
    cart.forEach(function (line) {
      var amount = lineAmount(line);
      subtotal += amount.raw;
      tax += amount.tax;
      grand += amount.total;
      count += line.quantity;
    });
    subtotalEl.textContent = formatMoney(round2(subtotal));
    taxEl.textContent = formatMoney(round2(tax));
    grandEl.textContent = formatMoney(round2(grand));
    cartCount.textContent = count + (count === 1 ? " item" : " items");
    checkoutButton.disabled = cart.length === 0 || inFlight;
    if (cart.length === 0) clearButton.classList.add("hidden");
    else clearButton.classList.remove("hidden");
  }

  function renderCart() {
    if (cart.length === 0) {
      cartEl.innerHTML =
        '<div class="empty-state h-full">' +
        '<span class="empty-icon"><svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg></span>' +
        '<h3 class="text-[15px] font-semibold">The bill is empty</h3>' +
        '<p class="text-muted mt-1 max-w-xs text-[13px]">Scanned and searched products will appear here.</p>' +
        "</div>";
      recalc();
      return;
    }

    var html = '<ul class="divide-y divide-line">';
    cart.forEach(function (line, index) {
      var amount = lineAmount(line);
      html +=
        '<li class="p-3.5 flex items-start gap-3" data-index="' + index + '">' +
        '<div class="flex-1 min-w-0">' +
        '<div class="font-medium text-ink text-[14px] leading-snug">' + escapeHtml(line.name) + "</div>" +
        '<div class="text-[12px] text-muted mt-0.5 tnum">' + formatMoney(line.price) + " · GST " + line.gst_rate + "%</div>" +
        "</div>" +
        '<div class="flex items-center rounded-lg border border-line bg-surface">' +
        '<button type="button" class="h-8 w-8 inline-flex items-center justify-center text-muted hover:text-ink hover:bg-app rounded-l-lg transition-colors" data-action="dec" aria-label="Decrease quantity">' + ICON.minus + "</button>" +
        '<input class="h-8 w-11 text-center text-sm tnum bg-transparent focus:outline-none" data-action="qty" type="number" min="1" value="' + line.quantity + '" aria-label="Quantity for ' + escapeHtml(line.name) + '">' +
        '<button type="button" class="h-8 w-8 inline-flex items-center justify-center text-muted hover:text-ink hover:bg-app rounded-r-lg transition-colors" data-action="inc" aria-label="Increase quantity">' + ICON.plus + "</button>" +
        "</div>" +
        '<div class="w-[86px] text-right shrink-0">' +
        '<div class="font-semibold tnum text-[14px]">' + formatMoney(amount.total) + "</div>" +
        '<div class="text-[11px] text-muted tnum">tax ' + formatMoney(amount.tax) + "</div>" +
        "</div>" +
        '<button type="button" class="btn-icon h-8 w-8 shrink-0 hover:text-danger hover:bg-danger/10" data-action="remove" aria-label="Remove ' + escapeHtml(line.name) + '">' + ICON.x + "</button>" +
        "</li>";
    });
    html += "</ul>";
    cartEl.innerHTML = html;
    recalc();
  }

  function focusScan() {
    var active = document.activeElement;
    var editing =
      active &&
      (active.tagName === "INPUT" || active.tagName === "SELECT") &&
      active !== scanInput;
    if (!editing && successPanel.classList.contains("hidden")) scanInput.focus();
  }

  function addProduct(product, quantity) {
    quantity = quantity || 1;
    var line = findLine(product.id);
    var desired = line ? line.quantity + quantity : quantity;
    if (desired > product.stock) {
      showFeedback("Only " + product.stock + " in stock — cannot add more.", "error");
      return;
    }
    if (line) {
      line.quantity = desired;
      line.stock = product.stock;
    } else {
      cart.push({
        id: product.id,
        name: product.name,
        price: parseFloat(product.price),
        gst_rate: parseFloat(product.gst_rate),
        stock: product.stock,
        quantity: quantity,
      });
    }
    pendingToken = null;
    showFeedback("Added " + product.name + " to the bill.", "success");
    renderCart();
    focusScan();
  }

  function doBarcodeLookup(code) {
    code = (code || "").trim();
    if (!code) return;
    fetch(lookupUrl + "?barcode=" + encodeURIComponent(code), {
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        if (data.found) addProduct(data.product, 1);
        else showFeedback(data.error || "No product matches barcode " + code + ".", "error");
      })
      .catch(function () {
        showFeedback("Could not reach the local server.", "error");
      });
  }

  var searchTimer = null;
  function scheduleSearch(term) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      runSearch(term);
    }, 160);
  }

  function runSearch(term) {
    term = term.trim();
    if (!term) {
      resultsEl.innerHTML =
        '<div class="empty-state h-full">' +
        '<span class="empty-icon"><svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.34-4.34"/></svg></span>' +
        '<h3 class="text-[15px] font-semibold">Ready to scan</h3>' +
        '<p class="text-muted mt-1 max-w-xs text-[13px]">Scan a product barcode or start typing a name to find items.</p>' +
        "</div>";
      return;
    }
    fetch(searchUrl + "?q=" + encodeURIComponent(term), {
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        renderResults(data.results || []);
      })
      .catch(function () {
        resultsEl.innerHTML =
          '<div class="flex flex-col items-center justify-center h-full text-center p-6 text-danger text-sm">' +
          '<p>Search failed. Check that the local server is running.</p></div>';
      });
  }

  function renderResults(products) {
    if (!products.length) {
      resultsEl.innerHTML =
        '<div class="empty-state h-full">' +
        '<span class="empty-icon"><svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16.5 9.4 7.5 4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg></span>' +
        '<h3 class="text-[15px] font-semibold">No matching products</h3>' +
        '<p class="text-muted mt-1 max-w-xs text-[13px]">No active product matches this search.</p>' +
        "</div>";
      return;
    }
    var html = '<ul class="space-y-1">';
    products.forEach(function (product) {
      var out = product.stock <= 0;
      var badge = out
        ? '<span class="badge-out">Out of stock</span>'
        : product.stock_status === "low"
        ? '<span class="badge-low">' + product.stock + " left</span>"
        : '<span class="badge-ok">' + product.stock + " in stock</span>";
      html +=
        '<li>' +
        '<button type="button" data-add-id="' + product.id + '"' + (out ? " disabled" : "") +
        ' class="w-full text-left flex items-center gap-3 rounded-lg px-3 py-3 transition-colors ' +
        (out ? "opacity-60 cursor-not-allowed" : "hover:bg-app") + '">' +
        '<div class="flex-1 min-w-0">' +
        '<div class="font-medium text-ink text-[14px] truncate">' + escapeHtml(product.name) + "</div>" +
        '<div class="text-[12px] text-muted mt-0.5 tnum">' + (product.barcode ? escapeHtml(product.barcode) + " · " : "") + formatMoney(parseFloat(product.price)) + " · GST " + product.gst_rate + "%</div>" +
        "</div>" +
        badge +
        '<span class="shrink-0 ml-1 inline-flex h-8 w-8 items-center justify-center rounded-lg border border-line text-muted">' + ICON.plus + "</span>" +
        "</button></li>";
    });
    html += "</ul>";
    resultsEl.innerHTML = html;

    Array.prototype.forEach.call(
      resultsEl.querySelectorAll("[data-add-id]"),
      function (button) {
        button.addEventListener("click", function () {
          if (button.disabled) return;
          var id = parseInt(button.getAttribute("data-add-id"), 10);
          for (var i = 0; i < products.length; i++) {
            if (products[i].id === id) {
              addProduct(products[i], 1);
              return;
            }
          }
        });
      }
    );
  }

  function changeQuantity(index, newQty) {
    var line = cart[index];
    if (!line) return;
    newQty = parseInt(newQty, 10);
    if (isNaN(newQty) || newQty < 1) newQty = 1;
    if (newQty > line.stock) {
      newQty = line.stock;
      showFeedback("Limited to available stock (" + line.stock + ").", "error");
    }
    line.quantity = newQty;
    pendingToken = null;
    renderCart();
  }

  function checkout() {
    if (inFlight || cart.length === 0) return;
    if (!pendingToken) {
      pendingToken =
        window.crypto && window.crypto.randomUUID
          ? window.crypto.randomUUID()
          : "tok-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    }
    inFlight = true;
    checkoutButton.disabled = true;
    checkoutLabel.textContent = "Saving…";
    checkoutError.classList.add("hidden");

    var payload = {
      token: pendingToken,
      payment_method: paymentSelect.value,
      items: cart.map(function (line) {
        return { product_id: line.id, quantity: line.quantity };
      }),
    };

    fetch(checkoutUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        inFlight = false;
        checkoutLabel.textContent = "Complete Sale";
        if (result.ok && result.data.ok) {
          successBill.textContent = result.data.bill_number;
          viewReceipt.setAttribute("href", result.data.receipt_url);
          printReceipt.setAttribute("href", result.data.receipt_url + "?print=1");
          successPanel.classList.remove("hidden");
          cart = [];
          pendingToken = null;
          paymentSelect.value = "";
          renderCart();
          clearTimeout(searchTimer);
          scanInput.value = "";
          resultsEl.innerHTML =
            '<div class="empty-state h-full"><span class="empty-icon"><svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.34-4.34"/></svg></span><h3 class="text-[15px] font-semibold">Ready to scan</h3><p class="text-muted mt-1 max-w-xs text-[13px]">Scan a product barcode or start typing a name to find items.</p></div>';
        } else {
          checkoutError.textContent =
            (result.data && result.data.error) || "Checkout failed. Please try again.";
          checkoutError.classList.remove("hidden");
          recalc();
        }
      })
      .catch(function () {
        inFlight = false;
        checkoutLabel.textContent = "Complete Sale";
        checkoutError.textContent =
          "Could not reach the local server. The bill is unchanged — try again.";
        checkoutError.classList.remove("hidden");
        recalc();
      });
  }

  function closeSuccess() {
    successPanel.classList.add("hidden");
    scanInput.focus();
  }

  /* Event wiring */
  scanInput.addEventListener("input", function () {
    showFeedback("");
    scheduleSearch(scanInput.value);
  });

  scanInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      var value = scanInput.value.trim();
      if (value) doBarcodeLookup(value);
    } else if (event.key === "Escape") {
      scanInput.value = "";
      showFeedback("");
      runSearch("");
    }
  });

  scanButton.addEventListener("click", function () {
    var value = scanInput.value.trim();
    if (value) doBarcodeLookup(value);
  });

  cartEl.addEventListener("click", function (event) {
    var button = event.target.closest("[data-action]");
    if (!button) return;
    var li = event.target.closest("[data-index]");
    if (!li) return;
    var index = parseInt(li.getAttribute("data-index"), 10);
    var action = button.getAttribute("data-action");
    if (action === "inc") changeQuantity(index, cart[index].quantity + 1);
    else if (action === "dec") changeQuantity(index, cart[index].quantity - 1);
    else if (action === "remove") {
      cart.splice(index, 1);
      pendingToken = null;
      renderCart();
    }
  });

  cartEl.addEventListener("change", function (event) {
    var input = event.target.closest("[data-action='qty']");
    if (!input) return;
    var li = event.target.closest("[data-index]");
    changeQuantity(parseInt(li.getAttribute("data-index"), 10), input.value);
  });

  clearButton.addEventListener("click", function () {
    if (cart.length && window.confirm("Clear all items from the current bill?")) {
      cart = [];
      pendingToken = null;
      renderCart();
    }
  });

  checkoutButton.addEventListener("click", checkout);
  newBillButton.addEventListener("click", closeSuccess);
  Array.prototype.forEach.call(
    document.querySelectorAll("[data-close-success]"),
    function (el) {
      el.addEventListener("click", closeSuccess);
    }
  );

  document.addEventListener("keydown", function (event) {
    if (event.key === "/" && document.activeElement !== scanInput) {
      var tag = document.activeElement && document.activeElement.tagName;
      if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") {
        event.preventDefault();
        scanInput.focus();
      }
    }
    if (event.key === "Escape" && !successPanel.classList.contains("hidden")) {
      closeSuccess();
    }
  });

  renderCart();
  scanInput.focus();
})();
