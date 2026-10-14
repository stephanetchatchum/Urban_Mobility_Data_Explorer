async function loadCharts(hour = "all") {
    const box = document.querySelector("#hourly-chart");

    try{
        const rows = await getSpeedByHour();
        box.replaceChildren();

        rows.forEach(row => {
            if (hour !== "all" && Number(row.hour) !== Number(hour)) {
                return;
            }

            const item = document.createElement("p");
            item.textContent =
                 `${row.hour}:00 - ${row.avg_speed} mph (${row.trip_count} trips)`;
            box.appendChild(item);
        });
    } catch (error) {
        box.textContent = "could not load hourly data.";
        console.error(error);
        
    }
}