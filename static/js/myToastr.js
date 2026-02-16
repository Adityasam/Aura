function show_toast(message, type="success"){
    document.getElementById("my-toastr").classList.remove("success");
    document.getElementById("my-toastr").classList.remove("warning");
    document.getElementById("my-toastr").classList.remove("show");

    document.getElementById("my-toastr").innerHTML = message;
    document.getElementById("my-toastr").classList.add(type);
    document.getElementById("my-toastr").classList.add("show");
    setTimeout(() => {
        document.getElementById("my-toastr").classList.remove("show");
    }, 1000)
}