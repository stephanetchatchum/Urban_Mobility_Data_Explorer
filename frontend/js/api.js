const API_BASE_URL = "http://127.0.0.1:5000";

async function getJSON(path) {
    const response = await fetch(`${API_BASE_URL}${path}`);

    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();

}

// turns {a: 1, b: ""} into "?a=1", empty values and "all" are left out
function buildQuery(params) {
    const parts = [];

    Object.keys(params).forEach(key => {
        const value = params[key];

        if (value === "" || value === "all" || value === null || value === undefined) {
            return;
        }
        parts.push(`${key}=${encodeURIComponent(value)}`);
    });

    return parts.length === 0 ? "" : `?${parts.join("&")}`;
}

function checkApiHealth() {
    return getJSON("/api/health");
}

function getZones() {
    return getJSON("/api/zones");
}

function getSlowestZones(hour = "all", dayType = "all") {
    const from = hour === "all" ? 8 : hour;
    const to = hour === "all" ? 9 : hour;
    return getJSON(`/api/story/slowest-zones${buildQuery({ n: 10, hour_from: from, hour_to: to, day_type: dayType })}`);
}

function getSpeedByHour(weekend = ""){
    const query = weekend === "" ? "" : `?weekend=${weekend}`;
    return getJSON(`/api/insights/speed-by-hour${query}`);
}

function getCostofSlowness(weekend = "") {
    const query = weekend === "" ? "" : `?weekend=${weekend}`;
    return getJSON(`/api/insights/cost-of-slowness${query}`);
}

function getHourProfile(dayType = "all") {
    return getJSON(`/api/story/hour-profile${buildQuery({ day_type: dayType })}`);
}

function getRawVsClean(dayType = "all") {
    return getJSON(`/api/trust/raw-vs-clean${buildQuery({ day_type: dayType })}`);
}

function getTrustSummary() {
    return getJSON("/api/trust/summary");
}

function getZoneShapes() {
    return getJSON("/api/zones/geojson");
}

function getZoneHour(hour, dayType = "all") {
    return getJSON(`/api/story/zone-hour${buildQuery({ hour: hour, day_type: dayType })}`);
}

function getTopRoutes() {
    return getJSON("/api/insights/top-routes?n=10");
}

function getEconomics(dayType = "all") {
    return getJSON(`/api/economics/by-hour${buildQuery({ day_type: dayType })}`);
}

function getHeatmap(metric = "trips") {
    return getJSON(`/api/time/heatmap${buildQuery({ metric: metric })}`);
}

function getTrips(params) {
    return getJSON(`/api/trips${buildQuery(params)}`);
}

function getTripDetails(id) {
    return getJSON(`/api/trips/${id}`);
}
