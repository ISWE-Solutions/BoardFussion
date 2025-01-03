/** @odoo-module **/

import { Component, onMounted, onWillStart, useRef} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";

class PDFCustomPreview extends Component {
    static template = "qxm_product_pdf_annotation_tool.PDFCustomPreview";
    static components = { Layout };

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.table_tbody = useRef("table_tbody");
        this.display = {
            controlPanel: {},
            searchPanel: false,
        };
        this.active_id = this.props.action.context.active_id;

        onWillStart(this.fetchDocumentData.bind(this));
        onMounted(this.initializePDF.bind(this));
    }

    async fetchDocumentData() {
            this.data = await this.rpc("/web/dataset/call_kw/product.document/get_document_data", {
            model: 'product.document',
            method: 'get_document_data',
            args: [this.active_id],
            kwargs: {},
        });
        console.log(this.data);
    }

    async initializePDF() {
        try {
            const pdfContainer = document.getElementById('pdf-container');
            pdfContainer.addEventListener('scroll', this.onScrollPage.bind(this));
            console.log('PDF container loaded',this.data);
            const typedarray = this.base64ToUint8Array(this.data.pdf.datas);

            const pdf = await pdfjsLib.getDocument({ data: typedarray }).promise;
            console.log('PDF loaded');

            const pageList = document.getElementById('page-list');

            for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                await this.renderPDFPage(pdf, pageNum, pdfContainer, pageList);
                
            }
            this.onScrollPage();
        } catch (reason) {
            console.error(reason);
        }
    }

    base64ToUint8Array(base64) {
        const binaryString = atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes;
    }

    async renderPDFPage(pdf, pageNum, pdfContainer, pageList) {
        const page = await pdf.getPage(pageNum);
        console.log('Page loaded');

        const scale = 1.3;
        const viewport = page.getViewport({ scale });
        const pageDiv = this.createPageDiv(pageNum);
        const canvasWrapper = this.createCanvasWrapper();
        const canvas = this.createCanvas(viewport);

        canvasWrapper.appendChild(canvas);
        pageDiv.appendChild(canvasWrapper);
        pdfContainer.appendChild(pageDiv);

        const pagerCanvasWrapper = await this.createPagerCanvasWrapper(page, pageNum, pageDiv, pdfContainer);
        pageList.appendChild(pagerCanvasWrapper);

        const context = canvas.getContext('2d');
        const renderContext = { canvasContext: context, viewport };
        await page.render(renderContext).promise;
        console.log('Page rendered');

        // this.initializeMarkers(pageNum, canvasWrapper, canvas);
        // this.initializeHighlightMarkers(pageNum, canvasWrapper, canvas);
        // this.initializeCanvas(pageNum, canvasWrapper, canvas);
    }

    createPageDiv(pageNum) {
        const pageDiv = document.createElement('div');
        pageDiv.id = `page-${pageNum}`;
        pageDiv.classList.add('page-div');
        return pageDiv;
    }

    createCanvasWrapper() {
        const canvasWrapper = document.createElement('div');
        canvasWrapper.classList.add('canvas-wrapper');
        return canvasWrapper;
    }

    createCanvas(viewport) {
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        return canvas;
    }

    async createPagerCanvasWrapper(page, pageNum, pageDiv, pdfContainer) {
        const pagerCanvasWrapper = document.createElement('div');
        pagerCanvasWrapper.id = `sidepage-${pageNum}`;
        pagerCanvasWrapper.classList.add('pager-canvas-wrapper');
        pagerCanvasWrapper.dataset.pageNumber = pageNum;

        const pagerViewport = page.getViewport({ scale: 0.2 });
        const pagerCanvas = this.createCanvas(pagerViewport);
        const pagerContext = pagerCanvas.getContext('2d');
        const renderPager = { canvasContext: pagerContext, viewport: pagerViewport };

        await page.render(renderPager).promise;

        const pageLink = document.createElement('div');
        pageLink.textContent = `${pageNum}`;

        pagerCanvasWrapper.appendChild(pagerCanvas);
        pagerCanvasWrapper.appendChild(pageLink);

        pagerCanvasWrapper.addEventListener('click', () => {
            this.scrollToPage(pageDiv, pdfContainer);
        });

        return pagerCanvasWrapper;
    }

    initializeMarkers(pageNum, canvasWrapper, canvas) {
        let line_count = 0;

//        canvas.addEventListener('click', async event => {
//            line_count += 1;
//            const { x, y } = this.getCanvasClickPosition(event, canvas);
//            const line_id = await this.createLine(x, y, pageNum);
//            console.log('Line created', line_id);
//            const line_data = await this.orm.searchRead(
//                "product.pdf.annotation.line",
//                [
//                  ["id", "=", line_id],
//                ],
//                ["user_id"]
//              );
//            console.log(line_data);
//            const user_name= line_data[0].user_id[1];
//            // console.log(user_name);
//            this.createMarkerDOM(x, y, "", line_id,user_name, canvasWrapper, pageNum, line_count);
//        });

        const lines = this.data.lines[pageNum] || [];
        for (const line of lines) {
            line_count += 1;
            this.createMarkerDOM(line.layerx, line.layery, line.description || "", line.id,line.user_id[1],canvasWrapper, pageNum, line_count);
        }
    }

    initializeHighlightMarkers(pageNum, canvasWrapper, canvas) {
        let marker_count = 0;

        const highlightMarkers = this.data.highlighted_marks[pageNum] || [];
        for (const marker of highlightMarkers) {
            marker_count += 1;
            this.createHighlighterDOM(marker.layerx, marker.layery, marker.height, marker.width || "", marker.id, canvasWrapper, pageNum, marker_count);
        }
    }

    initializeCanvas(pageNum, canvasWrapper, canvas){
        const ctx = canvas.getContext('2d');
        ctx.lineWidth = 3;
        const drawings = this.data.drawing[pageNum] || [];
        console.log('Drawings LOaded',drawings);
        for (const drawing of drawings) {
            const drawingData = JSON.parse(drawing.drawing_data);
            drawingData.forEach(data => {
                ctx.beginPath();
                ctx.moveTo(data[0].x, data[0].y);
                data.forEach(point => {
                    ctx.lineTo(point.x, point.y);
                });
                ctx.stroke();
            });
        }
    }

    createHighlighterDOM(x, y, height, width, highlighter_marker_id,canvasWrapper, pageNum, marker_count) {
        const hihglighterDiv = this.createHighlighterDiv(x, y, highlighter_marker_id, width, height );
        canvasWrapper.appendChild(hihglighterDiv);
        // this.removeHighlighterMarkerDiv(hihglighterDiv, highlighter_marker_id);
                                               
    }

    createHighlighterDiv(x, y, highlighter_marker_id, width, height) {
        const highlightDiv = document.createElement('div');
        highlightDiv.style.position = 'absolute';
        highlightDiv.style.left = `${x}px`;
        highlightDiv.style.top = `${y}px`;
        highlightDiv.style.width = `${width}px`;
        highlightDiv.style.height = `${height}px`;
        highlightDiv.style.backgroundColor = 'yellow';
        highlightDiv.style.opacity = '0.5';
        highlightDiv.id = `marker_${highlighter_marker_id}`;
        highlightDiv.classList.add('text_highlight');
        return highlightDiv;
    }

//    getCanvasClickPosition(event, canvas) {
//        const rect = canvas.getBoundingClientRect();
//        const x = (event.clientX - rect.left) - 3;
//        const y = (event.clientY - rect.top) - 4;
//        return { x, y };
//    }

    createMarkerDOM(x, y, description, line_id,user, canvasWrapper, pageNum, line_count) {
        console.log(user,'test');
        const markerDiv = this.createMarkerDiv(x, y, line_id);
        canvasWrapper.appendChild(markerDiv);

        const newTableRow = this.createTableRow(line_id, description,user, pageNum, line_count, markerDiv);
        this.table_tbody.el.appendChild(newTableRow);

        // this.makeDraggable(markerDiv, line_id); nOT IN READING VIEW
    }

    // OLD MARKER DIV FOR ANNOTATION
    // createMarkerDiv(x, y, line_id) {
    //     const markerDiv = document.createElement('div');
    //     markerDiv.style.left = `${x}px`;
    //     markerDiv.style.top = `${y}px`;
    //     markerDiv.id = `marker_${line_id}`;
    //     markerDiv.classList.add('img_marker');
    //     return markerDiv;
    // }

    createMarkerDiv(x, y, line_id) {
        const markerDiv = document.createElement('div');
        markerDiv.style.position = 'absolute'; // Ensure absolute positioning
        markerDiv.style.left = `${x}px`;
        markerDiv.style.top = `${y}px`;
        markerDiv.id = `marker_${line_id}`;
        markerDiv.classList.add('marker');

        // Create the Font Awesome icon element
        const icon = document.createElement('i');
        icon.classList.add('fa', 'fa-commenting');
        icon.style.color = 'red'; // Set the color of the icon
        icon.style.fontSize = '24px'; // Set the size of the icon

        // Append the icon to the markerDiv
        markerDiv.appendChild(icon);
        return markerDiv;
    }

    async createLine(x, y, page_no) {
        const [line_id] = await this.orm.create("product.pdf.annotation.line", [{
            page_no,
            layerx: x,
            layery: y,
            document_id: this.active_id
        }]);
        return line_id;
    }

    async updateLine(resId, data) {
        await this.orm.write("product.pdf.annotation.line", [resId], data);
    }

    // Make an element draggable
    makeDraggable(elem, line_id) {
        var self = this;
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

        elem.onmousedown = dragMouseDown;

        function dragMouseDown(e) {
            e = e || window.event;
            e.preventDefault();
            // Get the mouse cursor position at startup
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            // Call a function whenever the cursor moves
            document.onmousemove = elementDrag;
        }

        function elementDrag(e) {
            e = e || window.event;
            e.preventDefault();
            // Calculate the new cursor position
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;

            // Get the new position
            let newTop = elem.offsetTop - pos2;
            let newLeft = elem.offsetLeft - pos1;

            // Get parent boundaries
            const parentRect = elem.parentElement.getBoundingClientRect();
            const elemRect = elem.getBoundingClientRect();

            // Ensure the element stays within the parent's boundaries
            if (newTop < 0) {
                newTop = 0;
            } else if (newTop + elemRect.height > parentRect.height) {
                newTop = parentRect.height - elemRect.height;
            }

            if (newLeft < 0) {
                newLeft = 0;
            } else if (newLeft + elemRect.width > parentRect.width) {
                newLeft = parentRect.width - elemRect.width;
            }

            // Set the element's new position
            elem.style.top = newTop + "px";
            elem.style.left = newLeft + "px";
        }

        function closeDragElement(e) {
            // Stop moving when mouse button is released
            document.onmouseup = null;
            document.onmousemove = null;
            self.updateLine(line_id, { layerx: elem.style.left.replace('px', ''), layery: elem.style.top.replace('px', '') });
        }
    }

//     createTableRow(rowId, description,user, pageNumber, lineNumber, markerDiv) {
//         const tr = document.createElement('tr');
//         tr.id = `table_line_${rowId}`;
//         tr.className = 'table_tr_line';
//         tr.innerHTML = `
//             <th scope="row"><span>${pageNumber}</span></th>
//             <th scope="row"><span>${user}</span></th>
//             <td><span>${description}</span></td>
//         `;

//         tr.onmouseover = () => this.addHoverEffect(markerDiv, tr);
//         tr.onmouseout = () => this.removeHoverEffect();
//         tr.onclick = () => this.scrollToElement(markerDiv);

//         markerDiv.onmouseover = () => this.addHoverEffect(markerDiv, tr);
//         markerDiv.onmouseout = () => this.removeHoverEffect();
//         markerDiv.onclick = () => this.scrollToElement(tr);

// //        this.initializeDeleteMarker(tr, markerDiv, rowId);
// //        this.initializeSaveMarker(tr, rowId);

//         return tr;
//     }

    createTableRow(rowId, description, user, pageNumber, lineNumber, markerDiv) {
        const tr = document.createElement('tr');
        tr.id = `table_line_${rowId}`;
        tr.className = 'table_tr_line';
        tr.innerHTML = `
            <td>
                <div class="annotation-details">
                    <div><strong>Page:</strong> <span>${pageNumber}</span></div>
                    <div><strong>User:</strong> <span>${user}</span></div>
                    <div><strong>Comment:</strong></div>
                    <div><span>${description}</span></div>
                </div>
            </td>
        `;

        tr.onmouseover = () => this.addHoverEffect(markerDiv, tr);
        tr.onmouseout = () => this.removeHoverEffect();
        tr.onclick = () => this.scrollToElement(markerDiv);

        markerDiv.onmouseover = () => this.addHoverEffect(markerDiv, tr);
        markerDiv.onmouseout = () => this.removeHoverEffect();
        markerDiv.onclick = () => this.scrollToElement(tr);

        // this.initializeDeleteMarker(tr, markerDiv, rowId);
        // this.initializeSaveMarker(tr, rowId);

        return tr;
    }

    addHoverEffect(markerDiv, tr) {
        document.querySelectorAll('.marker_hover').forEach(el => el.classList.remove('marker_hover'));
        markerDiv.classList.add('marker_hover');
        tr.classList.add('marker_hover');
    }

    removeHoverEffect() {
        document.querySelectorAll('.marker_hover').forEach(el => el.classList.remove('marker_hover'));
    }

    scrollToElement(element) {
        const container = document.getElementById(element.classList.contains('marker') ? 'pdf-container' : 'description_container');
        const containerRect = container.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();

        const scrollTop = (elementRect.top - 200) - containerRect.top + container.scrollTop;

        container.scrollTo({ top: scrollTop, behavior: 'smooth' });
    }

    initializeDeleteMarker(tr, markerDiv, rowId) {
        const deleteIcon = tr.querySelector('.delete_marker');
        deleteIcon.onclick = () => {
            // First confirmation prompt
            const firstConfirmation = confirm("Are you sure you want to delete this item?");
            if (firstConfirmation) {
                    tr.remove();
                    markerDiv.remove();
                    this.orm.unlink("product.pdf.annotation.line", [rowId]);
            }
        };
    }

//    initializeDeleteMarker(tr, markerDiv, rowId) {
//        const deleteIcon = tr.querySelector('.delete_marker');
//        deleteIcon.onclick = () => {
//            tr.remove();
//            markerDiv.remove();
//            this.orm.unlink("product.pdf.annotation.line", [rowId]);
//        };
//    }

    initializeSaveMarker(tr, rowId) {
        const inputField = tr.querySelector('.table_tbody_input');
        inputField.onchange = () => {
            this.updateLine(rowId, { description: inputField.value });
        };
    }

    onScrollPage() {
        const pages = document.getElementById('pdf-container').querySelectorAll('[id^="page-"]');
        const pagerItems = document.getElementById('page-list').querySelectorAll('[id^="sidepage-"]');
        const scrollTop = document.getElementById('pdf-container').scrollTop;
        const containerHeight = document.getElementById('pdf-container').clientHeight;

        let currentPage = 0;
        pages.forEach((page, index) => {
            if (scrollTop >= page.offsetTop - containerHeight / 2) {
                currentPage = index;
            }
        });

        pagerItems.forEach((item, index) => {
            if (index === currentPage) {
                item.firstChild.classList.add('active');
                document.getElementById('page-list').scrollTop = item.offsetTop - document.getElementById('page-list').clientHeight / 2;
            } else {
                item.firstChild.classList.remove('active');
            }
        });
    }

    scrollToPage(pageDiv, pdfContainer) {
        const containerRect = pdfContainer.getBoundingClientRect();
        const pageRect = pageDiv.getBoundingClientRect();
        const scrollTop = pageRect.top - containerRect.top + pdfContainer.scrollTop;

        pdfContainer.scrollTop = scrollTop;
    }
}

registry.category("actions").add("qxm_product_pdf_annotation_tool.pdf_custom_preview", PDFCustomPreview);
