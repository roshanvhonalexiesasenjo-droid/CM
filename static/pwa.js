(() => {
  // Register the service worker (needs HTTPS or localhost)
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
    });
  }

  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (isStandalone) return;

  const DISMISS_KEY = "clubhouse-install-dismissed";
  const dismissed = () => { try { return localStorage.getItem(DISMISS_KEY) === "1"; } catch (e) { return false; } };
  const remember = () => { try { localStorage.setItem(DISMISS_KEY, "1"); } catch (e) {} };

  function banner(message, actionLabel, onAction) {
    if (dismissed() || document.querySelector(".install-banner")) return;
    const el = document.createElement("div");
    el.className = "install-banner";
    el.setAttribute("role", "dialog");
    el.innerHTML = '<span class="install-text"></span><span class="install-actions"></span>';
    el.querySelector(".install-text").textContent = message;
    const actions = el.querySelector(".install-actions");
    if (actionLabel) {
      const go = document.createElement("button");
      go.type = "button";
      go.textContent = actionLabel;
      go.addEventListener("click", () => { onAction(); el.remove(); });
      actions.appendChild(go);
    }
    const close = document.createElement("button");
    close.type = "button";
    close.className = "install-close";
    close.textContent = "Not now";
    close.addEventListener("click", () => { remember(); el.remove(); });
    actions.appendChild(close);
    document.body.appendChild(el);
  }

  // Android / Chrome / Edge (phone and PC)
  let deferred = null;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e;
    banner("Install Club Membership on this device for quick access.", "Install", async () => {
      deferred.prompt();
      await deferred.userChoice;
      deferred = null;
    });
  });
  window.addEventListener("appinstalled", () => {
    document.querySelector(".install-banner")?.remove();
    remember();
  });

  // iPhone / iPad Safari has no install prompt, so show instructions
  const ua = navigator.userAgent;
  const isIOS = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isSafari = /safari/i.test(ua) && !/crios|fxios|edgios/i.test(ua);
  if (isIOS && isSafari) {
    banner("To install: tap the Share button, then “Add to Home Screen”.", null, null);
  }
})();
