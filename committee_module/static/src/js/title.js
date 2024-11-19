console.log("Tab Title JS is being executed");

(function () {
    const desiredTitle = "Board Fusion";

    // Function to update the title
    function updateTitle() {
        if (document.title !== desiredTitle) {
            document.title = desiredTitle;
            console.log("Tab title updated to:", desiredTitle);
        }
    }

    // Check and update the title every 500ms
    setInterval(updateTitle, 500);
})();



// (function () {
//      document.addEventListener("DOMContentLoaded", function () {
//            document.title = "Board Fusion";
//            console.log("Tab title set to Board Fusion.");
//            });
//    })();