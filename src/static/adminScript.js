document.addEventListener("DOMContentLoaded", function() {
    const menuHTML = `
        <div id="overlay" onclick="toggleMenu()"></div>
        <div id="mySidebar" class="sidebar">
            <button class="close-btn" onclick="toggleMenu()">&times;</button>
            <div style="padding: 20px; color: #555; font-size: 12px;">ADMIN MENU</div>
            
            <a href="#" onclick="navigateTo('/bookmarks')">Bookmarks</a>
            <a href="#" onclick="navigateTo('/admin/requests')">Requests</a>
            <a href="#" onclick="navigateTo('/admin/dashboard')">Analytics</a>
            <a href="#" onclick="navigateTo('/upload')">Request Tracking</a>
            <a href="#" onclick="navigateTo('/admin/status')">Status</a>
            <a href="#" onclick="navigateTo('/admin/users')">User Management</a>
            <a href="#" onclick="navigateTo('/admin/manage_publications')">Manage Pubs</a>
            
            <a href="#" onclick="navigateTo('/logout')" style="margin-top: 50px; color: #ff6666;">Logout</a>
        </div>
    `;
    
    if (!document.getElementById('mySidebar')) {
        document.body.insertAdjacentHTML('afterbegin', menuHTML);
    }
});

function toggleMenu() {
    const sidebar = document.getElementById("mySidebar");
    const overlay = document.getElementById("overlay");
    if (sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        overlay.style.display = "none";
    } else {
        sidebar.classList.add('active');
        overlay.style.display = "block";
    }
}

function navigateTo(route) {
    window.location.href = route;
}