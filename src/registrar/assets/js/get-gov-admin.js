/**
 * @file get-gov-admin.js includes custom code for the .gov registrar admin portal.
 *
 * Constants and helper functions are at the top.
 * Event handlers are in the middle.
 * Initialization (run-on-load) stuff goes at the bottom.
 */

// <<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
// Helper functions.
/** Either sets attribute target="_blank" to a given element, or removes it */
function openInNewTab(el, removeAttribute = false){
    if(removeAttribute){
        el.setAttribute("target", "_blank");
    }else{
        el.removeAttribute("target", "_blank");
    }
};

// <<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
// Event handlers.

// <<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
// Initialization code.

/** An IIFE for pages in DjangoAdmin which may need custom JS implementation.
 * Currently only appends target="_blank" to the domain_form object,
 * but this can be expanded.
*/
(function (){
    /*
    On mouseover, appends target="_blank" on domain_form under the Domain page.
    The reason for this is that the template has a form that contains multiple buttons.
    The structure of that template complicates seperating those buttons 
    out of the form (while maintaining the same position on the page).
    However, if we want to open one of those submit actions to a new tab - 
    such as the manage domain button - we need to dynamically append target.
    As there is no built-in django method which handles this, we do it here. 
    */
    function prepareDjangoAdmin() {
        let domainFormElement = document.getElementById("domain_form");
        let domainSubmitButton = document.getElementById("manageDomainSubmitButton");
        if(domainSubmitButton && domainFormElement){
          domainSubmitButton.addEventListener("mouseover", () => openInNewTab(domainFormElement, true));
          domainSubmitButton.addEventListener("mouseout", () => openInNewTab(domainFormElement, false));
        }
    }

    prepareDjangoAdmin();
})();

/**
 * An IIFE to listen to changes on filter_horizontal and enable or disable the change/delete/view buttons as applicable
 *
 */
(function extendFilterHorizontalWidgets() {
    // Initialize custom filter_horizontal widgets; each widget has a "from" select list
    // and a "to" select list; initialization is based off of the presence of the
    // "to" select list
    checkToListThenInitWidget('id_other_contacts_to', 0);
    checkToListThenInitWidget('id_domain_info-0-other_contacts_to', 0);
    checkToListThenInitWidget('id_current_websites_to', 0);
    checkToListThenInitWidget('id_alternative_domains_to', 0);
})();

// Function to check for the existence of the "to" select list element in the DOM, and if and when found,
// initialize the associated widget
function checkToListThenInitWidget(toListId, attempts) {
    let toList = document.getElementById(toListId);
    attempts++;

    if (attempts < 6) {
        if ((toList !== null)) {
            // toList found, handle it
            // Add an event listener on the element
            // Add disabled buttons on the element's great-grandparent
            initializeWidgetOnToList(toList, toListId);
        } else {
            // Element not found, check again after a delay
            setTimeout(() => checkToListThenInitWidget(toListId, attempts), 1000); // Check every 1000 milliseconds (1 second)
        }
    }
}

// Initialize the widget:
//  add related buttons to the widget for edit, delete and view
//  add event listeners on the from list, the to list, and selector buttons which either enable or disable the related buttons
function initializeWidgetOnToList(toList, toListId) {
    // create the change button
    let changeLink = createAndCustomizeLink(
        toList,
        toListId,
        'related-widget-wrapper-link change-related',
        'Change',
        '/public/admin/img/icon-changelink.svg',
        {
            'contacts': '/admin/registrar/contact/__fk__/change/?_to_field=id&_popup=1',
            'websites': '/admin/registrar/website/__fk__/change/?_to_field=id&_popup=1',
            'alternative_domains': '/admin/registrar/website/__fk__/change/?_to_field=id&_popup=1',
        },
        true,
        true
    );

    let hasDeletePermission = hasDeletePermissionOnPage();

    let deleteLink = null;
    if (hasDeletePermission) {
        // create the delete button
        deleteLink = createAndCustomizeLink(
            toList,
            toListId,
            'related-widget-wrapper-link delete-related',
            'Delete',
            '/public/admin/img/icon-deletelink.svg',
            {
                'contacts': '/admin/registrar/contact/__fk__/delete/?_to_field=id&amp;_popup=1',
                'websites': '/admin/registrar/website/__fk__/delete/?_to_field=id&_popup=1',
                'alternative_domains': '/admin/registrar/website/__fk__/delete/?_to_field=id&_popup=1',
            },
            true,
            false
        );
    }

    // create the view button
    let viewLink = createAndCustomizeLink(
        toList,
        toListId,
        'related-widget-wrapper-link view-related',
        'View',
        '/public/admin/img/icon-viewlink.svg',
        {
            'contacts': '/admin/registrar/contact/__fk__/change/?_to_field=id',
            'websites': '/admin/registrar/website/__fk__/change/?_to_field=id',
            'alternative_domains': '/admin/registrar/website/__fk__/change/?_to_field=id',
        },
        false,
        false
    );

    // identify the fromList element in the DOM
    let fromList = toList.closest('.selector').querySelector(".selector-available select");

    fromList.addEventListener('click', function(event) {
        handleSelectClick(fromList, changeLink, deleteLink, viewLink);
    });
    
    toList.addEventListener('click', function(event) {
        handleSelectClick(toList, changeLink, deleteLink, viewLink);
    });
    
    // Disable buttons when the selectors are interacted with (items are moved from one column to the other)
    let selectorButtons = [];
    selectorButtons.push(toList.closest(".selector").querySelector(".selector-chooseall"));
    selectorButtons.push(toList.closest(".selector").querySelector(".selector-add"));
    selectorButtons.push(toList.closest(".selector").querySelector(".selector-remove"));

    selectorButtons.forEach((selector) => {
        selector.addEventListener("click", ()=>{disableRelatedWidgetButtons(changeLink, deleteLink, viewLink)});
      });
}

// create and customize the button, then add to the DOM, relative to the toList
//  toList - the element in the DOM for the toList
//  toListId - the ID of the element in the DOM
//  className - className to add to the created link
//  imgSrc - the img.src for the created link
//  imgAlt - the img.alt for the created link
//  dataMappings - dictionary which relates toListId to href for the created link
//  dataPopup - boolean for whether the link should produce a popup window
//  firstPosition - boolean indicating if link should be first position in list of links, otherwise, just before last link
function createAndCustomizeLink(toList, toListId, className, action, imgSrc, dataMappings, dataPopup, firstPosition) {
    // Create a link element
    var link = document.createElement('a');

    // Set class attribute for the link
    link.className = className;

    // Set id
    // Determine function {change, link, view} from the className
    // Add {function}_ to the beginning of the string
    let modifiedLinkString = className.split('-')[0] + '_' + toListId;
    // Remove '_to' from the end of the string
    modifiedLinkString = modifiedLinkString.replace('_to', '');
    link.id = modifiedLinkString;

    // Set data-href-template
    for (const [idPattern, template] of Object.entries(dataMappings)) {
        if (toListId.includes(idPattern)) {
            link.setAttribute('data-href-template', template);
            break; // Stop checking once a match is found
        }
    }

    if (dataPopup)
        link.setAttribute('data-popup', 'yes');
    
    link.setAttribute('title-template', action + " selected item")
    link.title = link.getAttribute('title-template');

    // Create an 'img' element
    var img = document.createElement('img');

    // Set attributes for the new image
    img.src = imgSrc;
    img.alt = action;

    // Append the image to the link
    link.appendChild(img);

    let relatedWidgetWrapper = toList.closest('.related-widget-wrapper');
    // Insert the link at the specified position
    if (firstPosition) {
        relatedWidgetWrapper.insertBefore(link, relatedWidgetWrapper.children[0]);
    } else {
        var lastChild = relatedWidgetWrapper.lastChild;

        // Check if lastChild is an element node (not a text node, comment, etc.)
        if (lastChild.nodeType === 1) {
            var previousSibling = lastChild.previousSibling;
            while (previousSibling.nodeType !== 1) {
                previousSibling = previousSibling.previousSibling;
            }
            relatedWidgetWrapper.insertBefore(link, previousSibling.nextSibling);
        }
    }

    // Return the link, which we'll use in the disable and enable functions
    return link;
}

// Either enable or disable widget buttons when select is clicked. Select can be in either the from list
// or the to list. Action (enable or disable) taken depends on the tocal count of selected items across
// both lists. If exactly one item is selected, buttons are enabled, and urls for the buttons associated
// with the selected item
function handleSelectClick(selectElement, changeLink, deleteLink, viewLink) {

    // If one item is selected (across selectElement and relatedSelectElement), enable buttons; otherwise, disable them
    if (selectElement.selectedOptions.length === 1) {
        // enable buttons for selected item in selectElement
        enableRelatedWidgetButtons(changeLink, deleteLink, viewLink, selectElement.selectedOptions[0].value, selectElement.selectedOptions[0].text);
    } else {
        disableRelatedWidgetButtons(changeLink, deleteLink, viewLink);
    }
}

function hasDeletePermissionOnPage() {
    return document.querySelector('.delete-related') != null
}

function disableRelatedWidgetButtons(changeLink, deleteLink, viewLink) {
    changeLink.removeAttribute('href');
    changeLink.setAttribute('title', changeLink.getAttribute('title-template'));
    if (deleteLink) {
        deleteLink.removeAttribute('href');
        deleteLink.setAttribute('title', deleteLink.getAttribute('title-template'));
    }
    viewLink.removeAttribute('href');
    viewLink.setAttribute('title', viewLink.getAttribute('title-template'));
}

function enableRelatedWidgetButtons(changeLink, deleteLink, viewLink, elementPk, elementText) {
    changeLink.setAttribute('href', changeLink.getAttribute('data-href-template').replace('__fk__', elementPk));
    changeLink.setAttribute('title', changeLink.getAttribute('title-template').replace('selected item', elementText));
    if (deleteLink) {
        deleteLink.setAttribute('href', deleteLink.getAttribute('data-href-template').replace('__fk__', elementPk));
        deleteLink.setAttribute('title', deleteLink.getAttribute('title-template').replace('selected item', elementText));
    }
    viewLink.setAttribute('href', viewLink.getAttribute('data-href-template').replace('__fk__', elementPk));
    viewLink.setAttribute('title', viewLink.getAttribute('title-template').replace('selected item', elementText));
}
