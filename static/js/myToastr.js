function show_toast(message, type="success"){
    const toast = document.getElementById("my-toastr");
    if (!toast) return;

    toast.classList.remove("success", "warning", "error", "show");
    void toast.offsetWidth; // Trigger reflow

    toast.innerHTML = message;
    toast.classList.add(type);
    toast.classList.add("show");
    
    setTimeout(() => {
        toast.classList.remove("show");
    }, 2500);
}