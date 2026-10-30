// Membaca nilai cookie, digunakan untuk mengambil token CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Men-toggle tombol like dan bookmark pada post
document.addEventListener("click", async(event) => {
    const button = event.target.closest(".likes-button, .bookmark-button");
    if (!button) {
        return;
    }

    const url = button.getAttribute("data-url");
    const response = await fetch(url, {
        method: "POST",
        headers: {"X-CSRFToken" : getCookie("csrftoken")},
    });

    if (!response) {
        return;
    }

    const data = await response.json()
    const button_active = data.toggle_command === "toggle";
    button.classList.toggle("active", button_active);

    if (button.classList.contains("likes-button")) {
        const counter = button.querySelector(".likes-counter");
        counter.textContent = parseInt(counter.textContent) + (button_active ? 1 : -1);
    }
});

// Membuka/menutup comment section pada post (untuk page beranda)
document.addEventListener("click", function(event) {
    const button = event.target.closest(".comment-button");
    if(!button) {
        return;
    }

    const post_wrapper = button.closest(".post-wrapper"); 
    const post = post_wrapper.querySelector(".post");
    const comment_section = post_wrapper.querySelector(".comment-section");
    
    comment_section.hidden = !comment_section.hidden;
    button.setAttribute("aria-pressed", String(!comment_section.hidden));
    button.classList.toggle("active", !comment_section.hidden);
    post.classList.toggle("post-comment-shown", !comment_section.hidden);
});

document.addEventListener("click", function(event) {
    const button = event.target.closest(".collapse-toggle-btn");
    if (!button) {
        return;
    }

    const post_content = button.closest(".post-body").querySelector(".post-content");
    const isCollapsed = post_content.classList.toggle("collapsed");
    if (!isCollapsed) {
        button.textContent = "Lihat Lebih Sedikit"
    } else {
        button.textContent = "Lihat Lebih Banyak"
    }
});