(function () {
    document.querySelectorAll("[data-tabs]").forEach(function (box) {
        var tabs = Array.prototype.slice.call(box.querySelectorAll('[role="tab"]'));
        var panels = Array.prototype.slice.call(box.querySelectorAll('[role="tabpanel"]'));
        var key = "tab:" + location.pathname + ":" + box.id;

        function show(panelId, remember) {
            tabs.forEach(function (tab) {
                var on = tab.getAttribute("data-panel") === panelId;
                tab.setAttribute("aria-selected", on ? "true" : "false");
                tab.classList.toggle("active", on);
                tab.tabIndex = on ? 0 : -1;
            });
            panels.forEach(function (panel) { panel.hidden = panel.id !== panelId; });
            if (remember) {
                try { sessionStorage.setItem(key, panelId); } catch (e) {}
            }
        }

        tabs.forEach(function (tab, i) {
            tab.addEventListener("click", function () { show(tab.getAttribute("data-panel"), true); });
            tab.addEventListener("keydown", function (event) {
                var next = event.key === "ArrowRight" ? i + 1 : event.key === "ArrowLeft" ? i - 1 : null;
                if (next === null) return;
                next = (next + tabs.length) % tabs.length;
                tabs[next].focus();
                show(tabs[next].getAttribute("data-panel"), true);
                event.preventDefault();
            });
        });

        var saved = null;
        try { saved = sessionStorage.getItem(key); } catch (e) {}
        show(saved && box.querySelector("#" + saved) ? saved : tabs[0].getAttribute("data-panel"), false);
    });
})();
