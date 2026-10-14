function setupFilters() {
    const form = document.querySelector("#filter-form");

    form.addEventListener("submit", async event => {
         event.preventDefault();

         const hour = document.querySelector("#hour-filter").value;
         const version = document.querySelector("#data-version").value;

          if (version === "raw") {
            message.textContent =
                "Raw data filtering is not available yet.";
            return;
        }

        await loadcharts(hour);
        message.textContent = "Filters applied successfully.";

    });
}