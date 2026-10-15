let zoneShapes = null;

async function loadZones() {
    const table = document.querySelector("#zone-results");

    try{
        const hour = document.querySelector("#hour-filter").value;
        const zones = await getSlowestZones(hour, readDayType());
        table.replaceChildren();

        zones.forEach((zone, index)  => {
            const row = document.createElement("tr");

            [
                index + 1,
                `${zone.zone} (${zone.borough})`,
                Number(zone.speed_mph).toFixed(1),
                Number(zone.min_per_mile).toFixed(1),
                Number(zone.trips).toLocaleString()

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

async function loadRoutes() {
    const table = document.querySelector("#route-results");

    try {
        const routes = await getTopRoutes();
        table.replaceChildren();

        routes.forEach((route, index) => {
            const row = document.createElement("tr");

            [
                index + 1,
                route.pickup_zone,
                route.dropoff_zone,
                Number(route.trips).toLocaleString(),
                `$${Number(route.avg_fare).toFixed(2)}`

            ].forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            table.appendChild(row);
        });
    } catch (error) {
        console.error(error);
        table.textContent = "Could not load the routes.";
    }
}

// light yellow (fast) to dark red (slow)
function zoneColor(value, smallest, largest) {
    const colors = ["#fef3c7", "#fdba74", "#f97316", "#c2410c", "#7c2d12"];
    const share = largest === smallest ? 0 : (value - smallest) / (largest - smallest);
    return colors[Math.min(colors.length - 1, Math.floor(share * colors.length))];
}

// draws the rings of a zone as one SVG path, longitude and latitude are turned into x and y
function zonePath(geometry, project) {
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    let path = "";

    polygons.forEach(polygon => {
        polygon.forEach(ring => {
            ring.forEach((point, index) => {
                const position = project(point[0], point[1]);
                path += `${index === 0 ? "M" : "L"}${position[0].toFixed(1)} ${position[1].toFixed(1)} `;
            });
            path += "Z ";
        });
    });

    return path;
}

async function loadMap() {
    const box = document.querySelector("#zone-map");
    const info = document.querySelector("#map-info");

    try {
        const filterHour = document.querySelector("#hour-filter").value;
        const hour = filterHour === "all" ? 8 : Number(filterHour);

        if (zoneShapes === null) {
            zoneShapes = await getZoneShapes();
        }
        const rows = combineDayTypes(await getZoneHour(hour, readDayType()), "location_id",
            ["median_min_per_mile", "median_speed_mph"]);

        // find the edges of the city, then scale it to a 700 wide picture (x is shrunk by cos of the latitude)
        let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90;
        zoneShapes.features.forEach(feature => {
            const polygons = feature.geometry.type === "Polygon" ? [feature.geometry.coordinates] : feature.geometry.coordinates;
            polygons.forEach(polygon => polygon[0].forEach(point => {
                minLon = Math.min(minLon, point[0]);
                maxLon = Math.max(maxLon, point[0]);
                minLat = Math.min(minLat, point[1]);
                maxLat = Math.max(maxLat, point[1]);
            }));
        });
        const squeeze = Math.cos(((minLat + maxLat) / 2) * Math.PI / 180);
        const scale = 700 / ((maxLon - minLon) * squeeze);
        const height = (maxLat - minLat) * scale;
        const project = (lon, lat) => [(lon - minLon) * squeeze * scale, (maxLat - lat) * scale];

        const reliable = rows.filter(row => row.trips >= 30 && row.median_min_per_mile !== null);
        const smallest = Math.min(...reliable.map(row => row.median_min_per_mile));
        const largest = Math.max(...reliable.map(row => row.median_min_per_mile));

        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", `0 0 700 ${height.toFixed(0)}`);
        svg.setAttribute("role", "img");
        svg.setAttribute("aria-label", "Map of taxi zones coloured by minutes per mile");

        zoneShapes.features.forEach(feature => {
            const id = feature.properties.location_id;
            const name = feature.properties.zone_name;
            const row = rows.find(item => item.location_id === id);
            const isReliable = row && row.trips >= 30 && row.median_min_per_mile !== null;

            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", zonePath(feature.geometry, project));
            path.setAttribute("fill", isReliable ? zoneColor(row.median_min_per_mile, smallest, largest) : "#e2e8f0");
            path.setAttribute("stroke", "#ffffff");
            path.setAttribute("stroke-width", "0.5");

            const text = isReliable
                ? `${name}: ${row.median_min_per_mile.toFixed(1)} min per mile, ${row.median_speed_mph.toFixed(1)} mph, ${row.trips} trips at ${hour}:00`
                : `${name}: fewer than 30 trips at ${hour}:00, not ranked`;
            const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
            title.textContent = text;
            path.appendChild(title);
            path.addEventListener("click", () => { info.textContent = text; });

            svg.appendChild(path);
        });

        box.replaceChildren(svg);
        box.classList.add("loaded");
        info.textContent = `Hour ${hour}:00. Lightest zone: ${smallest.toFixed(1)} min per mile. Darkest zone: ${largest.toFixed(1)} min per mile. Click a zone for details.`;
    } catch (error) {
        box.textContent = "Could not load the map.";
        console.error(error);
    }
}
