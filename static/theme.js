(() => {
    const key = "clubhouse-theme";
    const savedTheme = localStorage.getItem(key);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    document.documentElement.dataset.theme = savedTheme || (prefersDark ? "dark" : "light");

    document.addEventListener("DOMContentLoaded", () => {
        const toggle = document.querySelector(".theme-toggle");
        if (!toggle) return;

        const syncLabel = () => {
            const isDark = document.documentElement.dataset.theme === "dark";
            toggle.textContent = isDark ? "Light mode" : "Dark mode";
            toggle.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} mode`);
        };

        syncLabel();
        toggle.addEventListener("click", () => {
            const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
            document.documentElement.dataset.theme = theme;
            localStorage.setItem(key, theme);
            syncLabel();
        });
    });
})();
