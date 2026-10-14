async function loadZones()  {
    const table = document.querySelector("#zone-results");

    try{
        const zones = await getSlowestZones();
        table.replaceChildren();

        zones.forEach((zone, index)  => {
            const row = document.createElement("tr");

            [
                index + 1,
                zone.zone,
                zone.avg_speed,
                "30+ minimum"
            
            ].forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            table.appendChild(row);
    });
  } catch (error) {
        console.error(error);
        table.textContent = "Could not load zone rankings.";

  }

}