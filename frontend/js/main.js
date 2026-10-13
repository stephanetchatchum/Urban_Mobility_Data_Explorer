const filterForm = document.querySelector("#filter-form");
const resetButton = document.querySelector("#reset-filters");

const connectionStatus = document.querySelector("#connection-status");
const filterMessage = document.querySelector("#filter-message");
const pageMessage = document.querySelector("#page-Message");

function showMessage(element, message) {
    element.textcontent = message;
}

function getSelectedFilters() {
    const selectedHour = document.querySelector("#hour-filter").value;
    const selectedZone = document.querySelector("#zone-filter").value;
    const selectedVersion = document.querySelector("#data-version").value;

    return{
        hour: selectedHour,
        zone: selectedZone,
        version: selectedVersion
    };
}

function applyFilters(event) {
    event.preventDefault();

    const filters = getSelectedFilters();

    const selectedHour =
       filters.hour === "all" ? "all hours" : 'hour ${filters.hour}';

    const selectedZone = 
       filters.zone === "" ? "all pickup zones" : 'zone ${filters.zone}';

    showMessage(
        pageMessage,
        "filters are selected. They will affect the results once the backend API is connected."   
    );

    // The backend endpoint and supported query parameters are not known yet.
    // We will connect these filters after the team agrees on the API contract.

function resetFilters() {
    document.querySelector("#hour-filter").value = "all";
    document.querySelector("#zone-filter").value = "";
    document.querySelector("#data-version").value = "cleaned";

    showMessage(
        filterMessage,
        "filters have been reset. Apply filters to explore the data."
    );

    showMessage(
        pageMessage,
        "filters reset. Real statistics will appear here when the backend is connected."
    
    );
}


filterForm.addEventListener("submit", applyFilters);
resetButton.addEventListener("click", resetFilters);

showMessage(
    connectionStatus,
    "Waiting for backend"

);

showMessage(
    pageMessage,
    "the dashboard layout is ready. Live trip Statistics, rankings, and charts need the team API."

);


}