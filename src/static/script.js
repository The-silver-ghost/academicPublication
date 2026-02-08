document.addEventListener("DOMContentLoaded", function() {
    let role = document.body.dataset.role; 
    const path = window.location.pathname;

    if (!role) {
        if (path.includes('/admin/')) role = 'admin';
        else if (path.includes('/coordinator/')) role = 'coordinator';
        else if (path.includes('/academic/')) role = 'academic';
    }

    if (role === 'student' || role === 'lecturer') role = 'academic';

    let menuLinks = '';
    let homeLink = '/';

    if (role === 'admin') {
        homeLink = '/admin/home';
        menuLinks = `
            <a href="/admin/bookmarks"><i class="fas fa-bookmark"></i> Bookmarks</a>
            <a href="/admin/dashboard"><i class="fas fa-chart-pie"></i> Analytics</a>
            <a href="/admin/requests"><i class="fas fa-clipboard-list"></i> Request Tracking</a>
            <a href="/admin/status"><i class="fas fa-tasks"></i> Publication Status</a>
            <a href="/admin/users"><i class="fas fa-users-cog"></i> User Management</a>
        `;
    } else if (role === 'coordinator') {
        homeLink = '/coordinator/home';
        menuLinks = `
            <a href="/coordinator/bookmarks"><i class="fas fa-bookmark"></i> Bookmarks</a>
            <a href="/coordinator/dashboard"><i class="fas fa-chart-pie"></i> Analytics</a>
            <a href="/coordinator/requests"><i class="fas fa-clipboard-list"></i> Request Tracking</a>
            <a href="/coordinator/status"><i class="fas fa-tasks"></i> Publication Status</a>
        `;
    } else if (role === 'academic') { // Lecturer/Student
        homeLink = '/academic/home';
        menuLinks = `
            <a href="/academic/bookmarks"><i class="fas fa-bookmark"></i> Bookmarks</a>
            <a href="/academic/dashboard"><i class="fas fa-chart-pie"></i> Analytics</a>
            <a href="/academic/requests"><i class="fas fa-paper-plane"></i> Request Tracking</a>
            <a href="/academic/status"><i class="fas fa-tasks"></i> Publication Status</a>
        `;
    }

    if (menuLinks && !document.getElementById('mySidebar')) {
        const sidebarHTML = `
            <div id="overlay" onclick="toggleMenu()"></div>
            <div id="mySidebar" class="sidebar">
                <button class="close-btn" onclick="toggleMenu()">&times;</button>
                
                <div style="padding-top: 1rem;">
                    <a href="${homeLink}" class="menu-item highlight"><i class="fas fa-home"></i> Home</a>
                    <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 20px;">
                </div>

                <div class="menu-links">
                    ${menuLinks}
                </div>

                <div class="menu-footer">
                    <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 20px;">
                    <a href="/logout" class="menu-item logout"><i class="fas fa-sign-out-alt"></i> Logout</a>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('afterbegin', sidebarHTML);
    }
    
    document.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href && href.startsWith('/') && !href.startsWith('#') && this.target !== '_blank' && !href.startsWith('javascript')) {
                e.preventDefault();
                document.body.style.opacity = 0;
                setTimeout(() => { window.location.href = href; }, 150);
            }
        });
    });
});

function toggleMenu() {
    const sidebar = document.getElementById("mySidebar");
    const overlay = document.getElementById("overlay");
    if (!sidebar || !overlay) return;

    if (sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        overlay.style.opacity = "0";
        setTimeout(() => { overlay.style.display = "none"; }, 250);
    } else {
        overlay.style.display = "block";
        void overlay.offsetWidth; 
        overlay.style.opacity = "1";
        sidebar.classList.add('active');
    }
}

function toggleFilters() {
    var menu = document.getElementById("filterMenu");
    if(!menu) return;
    if (menu.style.display === "block") {
        menu.style.opacity = "0";
        setTimeout(() => { menu.style.display = "none"; }, 150);
    } else {
        menu.style.display = "block";
        setTimeout(() => { menu.style.opacity = "1"; }, 10);
    }
}

function previewImage(input) {
    const preview = document.getElementById('coverPreview');
    const placeholder = document.getElementById('previewText');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
            if(placeholder) placeholder.style.display = 'none';
        }
        reader.readAsDataURL(input.files[0]);
    }
}