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