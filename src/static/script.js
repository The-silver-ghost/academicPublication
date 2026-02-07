document.addEventListener("DOMContentLoaded", function() {
    // 1. Detect the current path to figure out the user role
    const path = window.location.pathname;
    let menuLinks = '';
    let homeLink = '/';


    // ADMIN -------------------------------------------------------
    if (path.includes('/admin/')) {
        homeLink = '/admin/home';
        menuLinks = `
            <a href="/admin/bookmarks">Bookmarks</a>
            <a href="/admin/requests">Review Requests</a>
            <a href="/admin/dashboard">Analytics</a>
            <a href="/admin/requests">Request Tracking</a>
            <a href="/admin/status">Status</a>
            <a href="/admin/users">User Management</a>
        `;
    } 

    // COORDINATOR ------------------------------------------------------
    else if (path.includes('/coordinator/')) {
        homeLink = '/coordinator/home';
        menuLinks = `
            <a href="/coordinator/bookmarks">Bookmarks</a>
            <a href="/coordinator/requests">Review Requests</a>
            <a href="/coordinator/dashboard">Analytics</a>
            <a href="/coordinator/requests">Request Tracking</a>
            <a href="/coordinator/status">Status</a>
        `;
    } 

    // LECTURER/STUDENT ---------------------------------------------------
    else if (path.includes('/academic/')) {
        homeLink = '/academic/home';
        menuLinks = `
            <a href="/academic/bookmarks">Bookmarks</a>
            <a href="/academic/dashboard">Analytics</a>
            <a href="/academic/requests">Request Tracking</a>
            <a href="/academic/status">Status</a>
        `;
    }

    const menuHTML = `
        <div id="overlay" onclick="toggleMenu()"></div>
        <div id="mySidebar" class="sidebar">
            <button class="close-btn" onclick="toggleMenu()">&times;</button>
            <div style="padding: 20px; color: #555; font-size: 12px; font-weight: bold; letter-spacing: 1px;">MENU</div>
            
            ${menuLinks}
            
            <hr style="border: 0; border-top: 1px solid #eee; margin: 10px 20px;">
            <a href="${homeLink}">Home</a>
            
            <a href="/logout" style="margin-top: 20px; color: #ff6666;">Logout</a>
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
        setTimeout(() => { overlay.style.display = "none"; }, 300);
    } else {
        overlay.style.display = "block";
        setTimeout(() => { sidebar.classList.add('active'); }, 10);
    }
}

function navigateTo(route) {
    window.location.href = route;
}

function goBack() {
    window.history.back();
}