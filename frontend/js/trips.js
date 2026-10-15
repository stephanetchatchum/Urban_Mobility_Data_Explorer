const tripState = { page: 1, sort: "time", order: "desc", totalPages: 1 };

function readTripFilters() {
    return {
        page: tripState.page,
        per_page: 20,
        sort: tripState.sort,
        order: tripState.order,
        min_distance: document.querySelector("#min-distance").value,
        max_distance: document.querySelector("#max-distance").value,
        min_fare: document.querySelector("#min-fare").value,
        max_fare: document.querySelector("#max-fare").value,
        start_date: document.querySelector("#start-date").value,
        end_date: document.querySelector("#end-date").value,
        pickup_zone: document.querySelector("#pickup-zone").value,
        dropoff_zone: document.querySelector("#dropoff-zone").value,
        hour: document.querySelector("#hour-filter").value
    };
}

async function loadTrips() {
    const table = document.querySelector("#trip-results");

    try {
        const result = await getTrips(readTripFilters());
        tripState.totalPages = Math.max(result.total_pages, 1);
        table.replaceChildren();

        if (result.data.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 7;
            cell.textContent = "No trips match these filters.";
            row.appendChild(cell);
            table.appendChild(row);
        }

        result.data.forEach(trip => {
            const row = document.createElement("tr");

            [
                trip.pickup_datetime,
                trip.pickup_zone || "-",
                trip.dropoff_zone || "-",
                `${trip.trip_distance.toFixed(2)} mi`,
                trip.duration_min === null ? "-" : trip.duration_min.toFixed(1),
                trip.speed_mph === null ? "-" : `${trip.speed_mph.toFixed(1)} mph`,
                `$${trip.fare_amount.toFixed(2)}`

            ].forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            row.addEventListener("click", () => showTripDetails(trip.trip_id));
            table.appendChild(row);
        });

        document.querySelector("#page-label").textContent =
            `Page ${result.page} of ${tripState.totalPages} (${Number(result.total).toLocaleString()} trips)`;
        document.querySelector("#prev-page").disabled = tripState.page <= 1;
        document.querySelector("#next-page").disabled = tripState.page >= tripState.totalPages;
    } catch (error) {
        console.error(error);
        table.textContent = "Could not load the trips.";
    }
}

async function showTripDetails(id) {
    const list = document.querySelector("#modal-details");

    try {
        const trip = await getTripDetails(id);
        list.replaceChildren();

        [
            ["Trip number", trip.trip_id],
            ["Pickup", `${trip.pickup_datetime} - ${trip.pickup_zone} (${trip.pickup_borough})`],
            ["Dropoff", `${trip.dropoff_datetime} - ${trip.dropoff_zone} (${trip.dropoff_borough})`],
            ["Distance", `${trip.trip_distance} mi`],
            ["Duration", `${trip.duration_min} min`],
            ["Speed", `${trip.speed_mph} mph`],
            ["Minutes per mile", trip.min_per_mile],
            ["Fare", `$${trip.fare_amount}`],
            ["Fare per minute", `$${trip.fare_per_min}`],
            ["Fare per mile", `$${trip.fare_per_mile}`],
            ["Tip", `$${trip.tip_amount}`],
            ["Total paid", `$${trip.total_amount}`],
            ["Payment", trip.payment_type],
            ["Rate code", trip.rate_code],
            ["Passengers", trip.passenger_count]

        ].forEach(pair => {
            const term = document.createElement("dt");
            term.textContent = pair[0];
            const detail = document.createElement("dd");
            detail.textContent = pair[1] === null || pair[1] === undefined ? "-" : pair[1];
            list.appendChild(term);
            list.appendChild(detail);
        });

        document.querySelector("#trip-modal").hidden = false;
    } catch (error) {
        console.error(error);
    }
}

async function loadZoneChoices() {
    try {
        const zones = await getZones();

        ["#pickup-zone", "#dropoff-zone"].forEach(selector => {
            const select = document.querySelector(selector);
            zones.forEach(zone => {
                const option = document.createElement("option");
                option.value = zone.location_id;
                option.textContent = `${zone.zone} (${zone.borough})`;
                select.appendChild(option);
            });
        });
    } catch (error) {
        console.error(error);
    }
}

function setupTrips() {
    document.querySelector("#trips-form").addEventListener("submit", event => {
        event.preventDefault();
        tripState.page = 1;
        loadTrips();
    });

    document.querySelectorAll("#trips-table th[data-sort]").forEach(header => {
        header.addEventListener("click", () => {
            const column = header.dataset.sort;
            tripState.order = tripState.sort === column && tripState.order === "desc" ? "asc" : "desc";
            tripState.sort = column;
            tripState.page = 1;
            loadTrips();
        });
    });

    document.querySelector("#prev-page").addEventListener("click", () => {
        tripState.page = Math.max(tripState.page - 1, 1);
        loadTrips();
    });

    document.querySelector("#next-page").addEventListener("click", () => {
        tripState.page = Math.min(tripState.page + 1, tripState.totalPages);
        loadTrips();
    });

    const modal = document.querySelector("#trip-modal");
    document.querySelector("#modal-close").addEventListener("click", () => { modal.hidden = true; });
    modal.addEventListener("click", event => {
        if (event.target === modal) {
            modal.hidden = true;
        }
    });
}
