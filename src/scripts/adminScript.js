document.addEventListener("DOMContentLoaded", function() {
    const menuHTML = `
        <div id="overlay" onclick="toggleMenu()"></div>
        <div id="mySidebar" class="sidebar">
            <button class="close-btn" onclick="toggleMenu()">&times;</button>
            <div style="padding: 20px; color: #555; font-size: 12px;">MENU</div>
            
            <a href="#" onclick="navigateTo('../mainScreens/bookmarks.html')">Bookmarks</a>
            <a href="#" onclick="navigateTo('../lecturerStudent/tracking_status.html')">Review</a>
            <a href="#" onclick="navigateTo('../mainScreens/analytics.html')">Analytics</a>
            <a href="#" onclick="navigateTo('../lecturerStudent/upload.html')">Request Tracking</a>
            <a href="#" onclick="navigateTo('../mainScreens/status.html')">Status</a>
            <a href="#" onclick="navigateTo('../mainScreens/status.html')">Users</a>
            <a href="#" onclick="navigateTo('../mainScreens/status.html')">Settings</a>
            
            <a href="#" onclick="navigateTo('../mainScreens/login.html')" style="margin-top: 50px; color: #ff6666;">Logout</a>
        </div>
    `;
    
    document.body.insertAdjacentHTML('afterbegin', menuHTML);
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

function navigateTo(page) {
    window.location.href = page;
}

function goBack() {
    window.history.back();
}