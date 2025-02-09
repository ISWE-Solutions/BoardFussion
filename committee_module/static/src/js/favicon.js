(function () {
    async function updateFavicon() {
        try {
            const response = await fetch('/web/image/res.company/1/logo?unique=' + new Date().getTime());
            if (response.ok) {
                const logoUrl = response.url;
                let link = document.querySelector("link[rel~='icon']");
                if (!link) {
                    link = document.createElement('link');
                    link.rel = 'icon';
                    document.head.appendChild(link);
                }
                link.href = logoUrl;
                console.log("Favicon updated to:", link.href);
            } else {
                console.error("Failed to fetch company logo.");
            }
        } catch (error) {
            console.error("Error fetching company logo:", error);
        }
    }

    updateFavicon();
})();
