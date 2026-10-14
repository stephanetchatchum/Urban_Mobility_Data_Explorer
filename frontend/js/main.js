
function showMessage(element, message) {
    element.textContent = message;
}

function resetFilters() {
    document.querySelector("#hour-filter").value = "all";
    document.querySelector("#data-version").value = "cleaned";

    showMessage(
        document.querySelector("#filter-message"),
        "Filters have been reset."
    );

    loadCharts();
}

document.addEventListener("DOMContentLoaded", async () => {
    const status = document.querySelector("#connection-status");
    const message = document.querySelector("#page-message");

    document.querySelector("#reset-filters")
        .addEventListener("click", resetFilters);

    try {
        await checkApiHealth();
        showMessage(status, "Backend connected");

        await loadCharts();
        await loadZones();

        setupFilters();

        showMessage(message, "Dashboard loaded successfully.");
    } catch (error) {
        showMessage(status, "Backend unavailable");
        showMessage(message, "Check that the backend server is running.");
        console.error(error);
    }
});


