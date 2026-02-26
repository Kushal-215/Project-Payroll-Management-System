// userHeader.js
(function() {
    // Get the logged-in employee ID from localStorage
    const empId = localStorage.getItem("empId");

    if (!empId) {
        console.warn("No empId found in localStorage. User might not be logged in.");
        // Optionally redirect to login page
        // window.location.href = "../public/login.html";
        return;
    }

    const API = "http://localhost:5000";

    // Load user info and update username in header
    async function loadUserHeader() {
        try {
            const res = await fetch(`${API}/user/${empId}`);
            
            if (!res.ok) {
                throw new Error(`User with ID ${empId} not found (status ${res.status})`);
            }

            const user = await res.json();

            // Update all elements with id="username" inside .welcome
            document.querySelectorAll(".welcome #username").forEach(el => {
                el.textContent = user.name || "User";
            });

        } catch (err) {
            console.error("Failed to load user info:", err);
            document.querySelectorAll(".welcome #username").forEach(el => {
                el.textContent = "User"; // fallback
            });
        }
    }

    // Call the function immediately
    loadUserHeader();
})();
document.addEventListener("DOMContentLoaded", async () => {
    const empId = localStorage.getItem("empId"); // ✅ read the stored id

    if(!empId) {
        console.error("No empId found. Redirecting to login...");
        window.location.href = "../public/login.html";
        return;
    }

    try {
        const res = await fetch(`http://localhost:5000/user/${empId}`);
        if(!res.ok) throw new Error("Failed to fetch user info");

        const user = await res.json();
        document.querySelectorAll(".username").forEach(el => {
            el.textContent = user.name;  // ✅ set username in all header elements
        });
    } catch(err) {
        console.error("Failed to load user info:", err);
    }
});