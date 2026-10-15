function showMessage(element, message) {
    element.textContent = message;
}

function resetFilters() {
    document.querySelector("#hour-filter").value = "all";
    document.querySelector("#day-type").value = "all";
    document.querySelector("#data-version").value = "cleaned";

    showMessage(
        document.querySelector("#filter-message"),
        "Filters have been reset."
    );

    tripState.page = 1;
    loadCharts();
    loadEconomics();
    loadZones();
    loadMap();
    loadTrips();
}

document.addEventListener("DOMContentLoaded", async () => {
    const status = document.querySelector("#connection-status");
    const message = document.querySelector("#page-message");

    document.querySelector("#reset-filters")
        .addEventListener("click", resetFilters);
    document.querySelector("#heatmap-metric")
        .addEventListener("change", loadHeatmap);

    try {
        await checkApiHealth();
        showMessage(status, "Backend connected");

        setupTrips();
        await loadZoneChoices();

        await loadCharts();
        await loadZones();
        await loadRoutes();
        await loadEconomics();
        await loadHeatmap();
        await loadTrust();
        await loadMap();
        await loadTrips();

        setupFilters();

        showMessage(message, "Dashboard loaded successfully.");
    } catch (error) {
        showMessage(status, "Backend unavailable");
        showMessage(message, "Check that the backend server is running.");
        console.error(error);
    }
});
