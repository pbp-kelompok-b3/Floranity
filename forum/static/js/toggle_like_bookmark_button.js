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