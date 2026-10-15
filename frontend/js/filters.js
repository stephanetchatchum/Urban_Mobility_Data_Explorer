function setupFilters() {
    const form = document.querySelector("#filter-form");
    const message = document.querySelector("#filter-message");

    form.addEventListener("submit", async event => {
         event.preventDefault();

         const hour = document.querySelector("#hour-filter").value;
         const version = document.querySelector("#data-version").value;

         message.textContent = "Updating the dashboard...";
         tripState.page = 1;

         await loadCharts(hour, version);
         await Promise.all([loadEconomics(), loadZones(), loadMap(), loadTrips()]);

         message.textContent = version === "raw"
            ? "Filters applied. Raw data only changes the hourly chart, the other views always use cleaned data."
            : "Filters applied successfully.";

    });
}
