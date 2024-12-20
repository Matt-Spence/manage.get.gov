/**
 * @file get-gov.js includes custom code for the .gov registrar.
 *
 * Constants and helper functions are at the top.
 * Event handlers are in the middle.
 * Initialization (run-on-load) stuff goes at the bottom.
 */


var DEFAULT_ERROR = "Please check this field for errors.";

var INFORMATIVE = "info";
var WARNING = "warning";
var ERROR = "error";
var SUCCESS = "success";

// <<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
// Helper functions.

/**
 * Hide element
 *
*/
const hideElement = (element) => {
  element.classList.add('display-none');
};

/**
* Show element
*
*/
const showElement = (element) => {
  element.classList.remove('display-none');
};

/**
 * Helper function to get the CSRF token from the cookie
 *
*/
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

/**
 * Helper function that scrolls to an element
 * @param {string} attributeName - The string "class" or "id"
 * @param {string} attributeValue - The class or id name
 */
function ScrollToElement(attributeName, attributeValue) {
  let targetEl = null;

  if (attributeName === 'class') {
    targetEl = document.getElementsByClassName(attributeValue)[0];
  } else if (attributeName === 'id') {
    targetEl = document.getElementById(attributeValue);
  } else {
    console.error('Error: unknown attribute name provided.');
    return; // Exit the function if an invalid attributeName is provided
  }

  if (targetEl) {
    const rect = targetEl.getBoundingClientRect();
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    window.scrollTo({
      top: rect.top + scrollTop,
      behavior: 'smooth' // Optional: for smooth scrolling
    });
  }
}

/** Makes an element invisible. */
function makeHidden(el) {
  el.style.position = "absolute";
  el.style.left = "-100vw";
  // The choice of `visiblity: hidden`
  // over `display: none` is due to
  // UX: the former will allow CSS
  // transitions when the elements appear.
  el.style.visibility = "hidden";
}

/** Makes visible a perviously hidden element. */
function makeVisible(el) {
  el.style.position = "relative";
  el.style.left = "unset";
  el.style.visibility = "visible";
}

/**
 * Toggles expand_more / expand_more svgs in buttons or anchors
 * @param {Element} element - DOM element
 */
function toggleCaret(element) {
  // Get a reference to the use element inside the button
  const useElement = element.querySelector('use');
  // Check if the span element text is 'Hide'
  if (useElement.getAttribute('xlink:href') === '/public/img/sprite.svg#expand_more') {
      // Update the xlink:href attribute to expand_more
      useElement.setAttribute('xlink:href', '/public/img/sprite.svg#expand_less');
  } else {
      // Update the xlink:href attribute to expand_less
      useElement.setAttribute('xlink:href', '/public/img/sprite.svg#expand_more');
  }
}

/**
 * Helper function that scrolls to an element
 * @param {string} attributeName - The string "class" or "id"
 * @param {string} attributeValue - The class or id name
 */
function ScrollToElement(attributeName, attributeValue) {
  let targetEl = null;

  if (attributeName === 'class') {
    targetEl = document.getElementsByClassName(attributeValue)[0];
  } else if (attributeName === 'id') {
    targetEl = document.getElementById(attributeValue);
  } else {
    console.error('Error: unknown attribute name provided.');
    return; // Exit the function if an invalid attributeName is provided
  }

  if (targetEl) {
    const rect = targetEl.getBoundingClientRect();
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    window.scrollTo({
      top: rect.top + scrollTop,
      behavior: 'smooth' // Optional: for smooth scrolling
    });
  }
}

/** Creates and returns a live region element. */
function createLiveRegion(id) {
  const liveRegion = document.createElement("div");
  liveRegion.setAttribute("role", "region");
  liveRegion.setAttribute("aria-live", "polite");
  liveRegion.setAttribute("id", id + "-live-region");
  liveRegion.classList.add("usa-sr-only");
  document.body.appendChild(liveRegion);
  return liveRegion;
}

/** Announces changes to assistive technology users. */
function announce(id, text) {
  let liveRegion = document.getElementById(id + "-live-region");
  if (!liveRegion) liveRegion = createLiveRegion(id);
  liveRegion.innerHTML = text;
}

/**
 * Slow down event handlers by limiting how frequently they fire.
 *
 * A wait period must occur with no activity (activity means "this
 * debounce function being called") before the handler is invoked.
 *
 * @param {Function} handler - any JS function
 * @param {number} cooldown - the wait period, in milliseconds
 */
function debounce(handler, cooldown=600) {
  let timeout;
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => handler.apply(context, args), cooldown);
  }
}

/** Asyncronously fetches JSON. No error handling. */
function fetchJSON(endpoint, callback, url="/api/v1/") {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', url + endpoint);
    xhr.send();
    xhr.onload = function() {
      if (xhr.status != 200) return;
      callback(JSON.parse(xhr.response));
    };
    // nothing, don't care
    // xhr.onerror = function() { };
}

/** Modifies CSS and HTML when an input is valid/invalid. */
function toggleInputValidity(el, valid, msg=DEFAULT_ERROR) {
  if (valid) {
    el.setCustomValidity("");
    el.removeAttribute("aria-invalid");
    el.classList.remove('usa-input--error');
  } else {
    el.classList.remove('usa-input--success');
    el.setAttribute("aria-invalid", "true");
    el.setCustomValidity(msg);
    el.classList.add('usa-input--error');
  }
}

/** Display (or hide) a message beneath an element. */
function inlineToast(el, id, style, msg) {
  if (!el.id && !id) {
    console.error("Elements must have an `id` to show an inline toast.");
    return;
  }
  let toast = document.getElementById((el.id || id) + "--toast");
  if (style) {
    if (!toast) {
      // create and insert the message div
      toast = document.createElement("div");
      const toastBody = document.createElement("div");
      const p = document.createElement("p");
      toast.setAttribute("id", (el.id || id) + "--toast");
      toast.className = `usa-alert usa-alert--${style} usa-alert--slim`;
      toastBody.classList.add("usa-alert__body");
      p.classList.add("usa-alert__text");
      p.innerHTML = msg;
      toastBody.appendChild(p);
      toast.appendChild(toastBody);
      el.parentNode.insertBefore(toast, el.nextSibling);
    } else {
      // update and show the existing message div
      toast.className = `usa-alert usa-alert--${style} usa-alert--slim`;
      toast.querySelector("div p").innerHTML = msg;
      makeVisible(toast);
    }
  } else {
    if (toast) makeHidden(toast);
  }
}

function checkDomainAvailability(el) {
  const callback = (response) => {
    toggleInputValidity(el, (response && response.available), msg=response.message);
    announce(el.id, response.message);

    // Determines if we ignore the field if it is just blank
    ignore_blank = el.classList.contains("blank-ok")
    if (el.validity.valid) {
      el.classList.add('usa-input--success');
      // use of `parentElement` due to .gov inputs being wrapped in www/.gov decoration
      inlineToast(el.parentElement, el.id, SUCCESS, response.message);
    } else if (ignore_blank && response.code == "required"){
      // Visually remove the error
      error = "usa-input--error"
      if (el.classList.contains(error)){
        el.classList.remove(error)
      }
    } else {
      inlineToast(el.parentElement, el.id, ERROR, response.message);
    }
  }
  fetchJSON(`available/?domain=${el.value}`, callback);
}

/** Hides the toast message and clears the aira live region. */
function clearDomainAvailability(el) {
  el.classList.remove('usa-input--success');
  announce(el.id, "");
  // use of `parentElement` due to .gov inputs being wrapped in www/.gov decoration
  inlineToast(el.parentElement, el.id);
}

/** Runs all the validators associated with this element. */
function runValidators(el) {
  const attribute = el.getAttribute("validate") || "";
  if (!attribute.length) return;
  const validators = attribute.split(" ");
  let isInvalid = false;
  for (const validator of validators) {
    switch (validator) {
      case "domain":
        checkDomainAvailability(el);
        break;
    }
  }
  toggleInputValidity(el, !isInvalid);
}

/** Clears all the validators associated with this element. */
function clearValidators(el) {
  const attribute = el.getAttribute("validate") || "";
  if (!attribute.length) return;
  const validators = attribute.split(" ");
  for (const validator of validators) {
    switch (validator) {
      case "domain":
        clearDomainAvailability(el);
        break;
    }
  }
  toggleInputValidity(el, true);
}

/** Hookup listeners for yes/no togglers for form fields 
 * Parameters:
 *  - radioButtonName:  The "name=" value for the radio buttons being used as togglers
 *  - elementIdToShowIfYes: The Id of the element (eg. a div) to show if selected value of the given
 * radio button is true (hides this element if false)
 *  - elementIdToShowIfNo: The Id of the element (eg. a div) to show if selected value of the given
 * radio button is false (hides this element if true)
 * **/
function HookupYesNoListener(radioButtonName, elementIdToShowIfYes, elementIdToShowIfNo) {
  HookupRadioTogglerListener(radioButtonName, {
    'True': elementIdToShowIfYes,
    'False': elementIdToShowIfNo
  });
}

/** 
 * Hookup listeners for radio togglers in form fields.
 * 
 * Parameters:
 *  - radioButtonName: The "name=" value for the radio buttons being used as togglers
 *  - valueToElementMap: An object where keys are the values of the radio buttons, 
 *    and values are the corresponding DOM element IDs to show. All other elements will be hidden.
 * 
 * Usage Example:
 * Assuming you have radio buttons with values 'option1', 'option2', and 'option3',
 * and corresponding DOM IDs 'section1', 'section2', 'section3'.
 * 
 * HookupValueBasedListener('exampleRadioGroup', {
 *      'option1': 'section1',
 *      'option2': 'section2',
 *      'option3': 'section3'
 *    });
 **/
function HookupRadioTogglerListener(radioButtonName, valueToElementMap) {
  // Get the radio buttons
  let radioButtons = document.querySelectorAll('input[name="'+radioButtonName+'"]');
  
  // Extract the list of all element IDs from the valueToElementMap
  let allElementIds = Object.values(valueToElementMap);

  function handleRadioButtonChange() {
    // Find the checked radio button
    let radioButtonChecked = document.querySelector('input[name="'+radioButtonName+'"]:checked');
    let selectedValue = radioButtonChecked ? radioButtonChecked.value : null;

    // Hide all elements by default
    allElementIds.forEach(function (elementId) {
      let element = document.getElementById(elementId);
      if (element) {
        hideElement(element);
      }
    });

    // Show the relevant element for the selected value
    if (selectedValue && valueToElementMap[selectedValue]) {
      let elementToShow = document.getElementById(valueToElementMap[selectedValue]);
      if (elementToShow) {
        showElement(elementToShow);
      }
    }
  }

  if (radioButtons.length) {
    // Add event listener to each radio button
    radioButtons.forEach(function (radioButton) {
      radioButton.addEventListener('change', handleRadioButtonChange);
    });

    // Initialize by checking the current state
    handleRadioButtonChange();
  }
}


// A generic display none/block toggle function that takes an integer param to indicate how the elements toggle
function toggleTwoDomElements(ele1, ele2, index) {
  let element1 = document.getElementById(ele1);
  let element2 = document.getElementById(ele2);
  if (element1 || element2) {
      // Toggle display based on the index
      if (element1) {element1.style.display = index === 1 ? 'block' : 'none';}
      if (element2) {element2.style.display = index === 2 ? 'block' : 'none';}
  } 
  else {
      console.error('Unable to find elements to toggle');
  }
}

// <<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
// Event handlers.

/** On input change, handles running any associated validators. */
function handleInputValidation(e) {
  clearValidators(e.target);
  if (e.target.hasAttribute("auto-validate")) runValidators(e.target);
}

/** On button click, handles running any associated validators. */
function validateFieldInput(e) {
  const attribute = e.target.getAttribute("validate-for") || "";
  if (!attribute.length) return;
  const input = document.getElementById(attribute);
  removeFormErrors(input, true);
  runValidators(input);
}


function validateFormsetInputs(e, availabilityButton) {

  // Collect input IDs from the repeatable forms
  let inputs = Array.from(document.querySelectorAll('.repeatable-form input'))

  // Run validators for each input
  inputs.forEach(input => {
    removeFormErrors(input, true);
    runValidators(input);
  });

  // Set the validate-for attribute on the button with the collected input IDs
  // Not needed for functionality but nice for accessibility
  inputs = inputs.map(input => input.id).join(', ');
  availabilityButton.setAttribute('validate-for', inputs);

}

// <<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
// Initialization code.

/**
 * An IIFE that will attach validators to inputs.
 *
 * It looks for elements with `validate="<type> <type>"` and adds change handlers.
 * 
 * These handlers know about two other attributes:
 *  - `validate-for="<id>"` creates a button which will run the validator(s) on <id>
 *  - `auto-validate` will run validator(s) when the user stops typing (otherwise,
 *     they will only run when a user clicks the button with `validate-for`)
 */
 (function validatorsInit() {
  "use strict";
  const needsValidation = document.querySelectorAll('[validate]');
  for(const input of needsValidation) {
    input.addEventListener('input', handleInputValidation);
  }
  const alternativeDomainsAvailability = document.getElementById('validate-alt-domains-availability');
  const activatesValidation = document.querySelectorAll('[validate-for]');

  for(const button of activatesValidation) {
    // Adds multi-field validation for alternative domains
    if (button === alternativeDomainsAvailability) {
      button.addEventListener('click', (e) => {
        validateFormsetInputs(e, alternativeDomainsAvailability)
      });
    } else {
      button.addEventListener('click', validateFieldInput);
    }
  }
})();

/**
 * Removes form errors surrounding a form input
 */
function removeFormErrors(input, removeStaleAlerts=false){
  // Remove error message
  let errorMessage = document.getElementById(`${input.id}__error-message`);
  if (errorMessage) {
    errorMessage.remove();
  }else{
    return
  }

  // Remove error classes
  if (input.classList.contains('usa-input--error')) {
    input.classList.remove('usa-input--error');
  }

  // Get the form label
  let label = document.querySelector(`label[for="${input.id}"]`);
  if (label) {
    label.classList.remove('usa-label--error');

    // Remove error classes from parent div
    let parentDiv = label.parentElement;
    if (parentDiv) {
      parentDiv.classList.remove('usa-form-group--error');
    }
  }

  if (removeStaleAlerts){
    let staleAlerts = document.querySelectorAll(".usa-alert--error")
    for (let alert of staleAlerts){
      // Don't remove the error associated with the input
      if (alert.id !== `${input.id}--toast`) {
        alert.remove()
      }
    }
  }
}

/**
 * Prepare the namerservers and DS data forms delete buttons
 * We will call this on the forms init, and also every time we add a form
 * 
 */
function removeForm(e, formLabel, isNameserversForm, addButton, formIdentifier){
  let totalForms = document.querySelector(`#id_${formIdentifier}-TOTAL_FORMS`);
  let formToRemove = e.target.closest(".repeatable-form");
  formToRemove.remove();
  let forms = document.querySelectorAll(".repeatable-form");
  totalForms.setAttribute('value', `${forms.length}`);

  let formNumberRegex = RegExp(`form-(\\d){1}-`, 'g');
  let formLabelRegex = RegExp(`${formLabel} (\\d+){1}`, 'g');
  // For the example on Nameservers
  let formExampleRegex = RegExp(`ns(\\d+){1}`, 'g');

  forms.forEach((form, index) => {
    // Iterate over child nodes of the current element
    Array.from(form.querySelectorAll('label, input, select')).forEach((node) => {
      // Iterate through the attributes of the current node
      Array.from(node.attributes).forEach((attr) => {
        // Check if the attribute value matches the regex
        if (formNumberRegex.test(attr.value)) {
          // Replace the attribute value with the updated value
          attr.value = attr.value.replace(formNumberRegex, `form-${index}-`);
        }
      });
    });

    // h2 and legend for DS form, label for nameservers  
    Array.from(form.querySelectorAll('h2, legend, label, p')).forEach((node) => {

      let innerSpan = node.querySelector('span')
      if (innerSpan) {
        innerSpan.textContent = innerSpan.textContent.replace(formLabelRegex, `${formLabel} ${index + 1}`);
      } else {
        node.textContent = node.textContent.replace(formLabelRegex, `${formLabel} ${index + 1}`);
        node.textContent = node.textContent.replace(formExampleRegex, `ns${index + 1}`);
      }
      
      // If the node is a nameserver label, one of the first 2 which was previously 3 and up (not required)
      // inject the USWDS required markup and make sure the INPUT is required
      if (isNameserversForm && index <= 1 && node.innerHTML.includes('server') && !node.innerHTML.includes('*')) {

        // Remove the word optional
        innerSpan.textContent = innerSpan.textContent.replace(/\s*\(\s*optional\s*\)\s*/, '');

        // Create a new element
        const newElement = document.createElement('abbr');
        newElement.textContent = '*';
        newElement.setAttribute("title", "required");
        newElement.classList.add("usa-hint", "usa-hint--required");

        // Append the new element to the label
        node.appendChild(newElement);
        // Find the next sibling that is an input element
        let nextInputElement = node.nextElementSibling;

        while (nextInputElement) {
          if (nextInputElement.tagName === 'INPUT') {
            // Found the next input element
            nextInputElement.setAttribute("required", "")
            break;
          }
          nextInputElement = nextInputElement.nextElementSibling;
        }
        nextInputElement.required = true;
      }

      
    
    });

    // Display the add more button if we have less than 13 forms
    if (isNameserversForm && forms.length <= 13) {
      addButton.removeAttribute("disabled");
    }

    if (isNameserversForm && forms.length < 3) {
      // Hide the delete buttons on the remaining nameservers
      Array.from(form.querySelectorAll('.delete-record')).forEach((deleteButton) => {
        deleteButton.setAttribute("disabled", "true");
      });
    }
  
  });
}

/**
 * Delete method for formsets using the DJANGO DELETE widget (Other Contacts)
 * 
 */
function markForm(e, formLabel){
  // Unlike removeForm, we only work with the visible forms when using DJANGO's DELETE widget
  let totalShownForms = document.querySelectorAll(`.repeatable-form:not([style*="display: none"])`).length;

  if (totalShownForms == 1) {
    // toggle the radio buttons
    let radioButton = document.querySelector('input[name="other_contacts-has_other_contacts"][value="False"]');
    radioButton.checked = true;
    // Trigger the change event
    let event = new Event('change');
    radioButton.dispatchEvent(event);
  } else {

    // Grab the hidden delete input and assign a value DJANGO will look for
    let formToRemove = e.target.closest(".repeatable-form");
    if (formToRemove) {
      let deleteInput = formToRemove.querySelector('input[class="deletion"]');
      if (deleteInput) {
        deleteInput.value = 'on';
      }
    }

    // Set display to 'none'
    formToRemove.style.display = 'none';
  }
  
  // Update h2s on the visible forms only. We won't worry about the forms' identifiers
  let shownForms = document.querySelectorAll(`.repeatable-form:not([style*="display: none"])`);
  let formLabelRegex = RegExp(`${formLabel} (\\d+){1}`, 'g');
  shownForms.forEach((form, index) => {
    // Iterate over child nodes of the current element
    Array.from(form.querySelectorAll('h2')).forEach((node) => {
        node.textContent = node.textContent.replace(formLabelRegex, `${formLabel} ${index + 1}`);
    });
  });
}

/**
 * Prepare the namerservers, DS data and Other Contacts formsets' delete button
 * for the last added form. We call this from the Add function
 * 
 */
function prepareNewDeleteButton(btn, formLabel) {
  let formIdentifier = "form"
  let isNameserversForm = document.querySelector(".nameservers-form");
  let isOtherContactsForm = document.querySelector(".other-contacts-form");
  let addButton = document.querySelector("#add-form");

  if (isOtherContactsForm) {
    formIdentifier = "other_contacts";
    // We will mark the forms for deletion
    btn.addEventListener('click', function(e) {
      markForm(e, formLabel);
    });
  } else {
    // We will remove the forms and re-order the formset
    btn.addEventListener('click', function(e) {
      removeForm(e, formLabel, isNameserversForm, addButton, formIdentifier);
    });
  }
}

/**
 * Prepare the namerservers, DS data and Other Contacts formsets' delete buttons
 * We will call this on the forms init
 * 
 */
function prepareDeleteButtons(formLabel) {
  let formIdentifier = "form"
  let deleteButtons = document.querySelectorAll(".delete-record");
  let isNameserversForm = document.querySelector(".nameservers-form");
  let isOtherContactsForm = document.querySelector(".other-contacts-form");
  let addButton = document.querySelector("#add-form");
  if (isOtherContactsForm) {
    formIdentifier = "other_contacts";
  }
  
  // Loop through each delete button and attach the click event listener
  deleteButtons.forEach((deleteButton) => {
    if (isOtherContactsForm) {
      // We will mark the forms for deletion
      deleteButton.addEventListener('click', function(e) {
        markForm(e, formLabel);
      });
    } else {
      // We will remove the forms and re-order the formset
      deleteButton.addEventListener('click', function(e) {
        removeForm(e, formLabel, isNameserversForm, addButton, formIdentifier);
      });
    }
  });
}

/**
 * DJANGO formset's DELETE widget
 * On form load, hide deleted forms, ie. those forms with hidden input of class 'deletion'
 * with value='on'
 */
function hideDeletedForms() {
  let hiddenDeleteButtonsWithValueOn = document.querySelectorAll('input[type="hidden"].deletion[value="on"]');

  // Iterating over the NodeList of hidden inputs
  hiddenDeleteButtonsWithValueOn.forEach(function(hiddenInput) {
      // Finding the closest parent element with class "repeatable-form" for each hidden input
      var repeatableFormToHide = hiddenInput.closest('.repeatable-form');
  
      // Checking if a matching parent element is found for each hidden input
      if (repeatableFormToHide) {
          // Setting the display property to "none" for each matching parent element
          repeatableFormToHide.style.display = 'none';
      }
  });
}

// Checks for if we want to display Urbanization or not
document.addEventListener('DOMContentLoaded', function() {
  var stateTerritoryField = document.querySelector('select[name="organization_contact-state_territory"]');

  if (!stateTerritoryField) {
    return; // Exit if the field not found
  }

  setupUrbanizationToggle(stateTerritoryField);
});

function setupUrbanizationToggle(stateTerritoryField) {
  var urbanizationField = document.getElementById('urbanization-field');
  
  function toggleUrbanizationField() {
    // Checking specifically for Puerto Rico only
    if (stateTerritoryField.value === 'PR') { 
      urbanizationField.style.display = 'block';
    } else {
      urbanizationField.style.display = 'none';
    }
  }

  toggleUrbanizationField();

  stateTerritoryField.addEventListener('change', toggleUrbanizationField);
}

/**
 * An IIFE that attaches a click handler for our dynamic formsets
 *
 * Only does something on a few pages, but it should be fast enough to run
 * it everywhere.
 */
(function prepareFormsetsForms() {
  let formIdentifier = "form"
  let repeatableForm = document.querySelectorAll(".repeatable-form");
  let container = document.querySelector("#form-container");
  let addButton = document.querySelector("#add-form");
  let cloneIndex = 0;
  let formLabel = '';
  let isNameserversForm = document.querySelector(".nameservers-form");
  let isOtherContactsForm = document.querySelector(".other-contacts-form");
  let isDsDataForm = document.querySelector(".ds-data-form");
  let isDotgovDomain = document.querySelector(".dotgov-domain-form");
  // The Nameservers formset features 2 required and 11 optionals
  if (isNameserversForm) {
    // cloneIndex = 2;
    formLabel = "Name server";
  // DNSSEC: DS Data
  } else if (isDsDataForm) {
    formLabel = "DS data record";
  // The Other Contacts form
  } else if (isOtherContactsForm) {
    formLabel = "Organization contact";
    container = document.querySelector("#other-employees");
    formIdentifier = "other_contacts"
  } else if (isDotgovDomain) {
    formIdentifier = "dotgov_domain"
  }
  let totalForms = document.querySelector(`#id_${formIdentifier}-TOTAL_FORMS`);

  // On load: Disable the add more button if we have 13 forms
  if (isNameserversForm && document.querySelectorAll(".repeatable-form").length == 13) {
    addButton.setAttribute("disabled", "true");
  }

  // Hide forms which have previously been deleted
  hideDeletedForms()

  // Attach click event listener on the delete buttons of the existing forms
  prepareDeleteButtons(formLabel);

  if (addButton)
    addButton.addEventListener('click', addForm);

  function addForm(e){
      let forms = document.querySelectorAll(".repeatable-form");
      let formNum = forms.length;
      let newForm = repeatableForm[cloneIndex].cloneNode(true);
      let formNumberRegex = RegExp(`${formIdentifier}-(\\d){1}-`,'g');
      let formLabelRegex = RegExp(`${formLabel} (\\d){1}`, 'g');
      // For the eample on Nameservers
      let formExampleRegex = RegExp(`ns(\\d){1}`, 'g');

      // Some Nameserver form checks since the delete can mess up the source object we're copying
      // in regards to required fields and hidden delete buttons
      if (isNameserversForm) {

        // If the source element we're copying has required on an input,
        // reset that input
        let formRequiredNeedsCleanUp = newForm.innerHTML.includes('*');
        if (formRequiredNeedsCleanUp) {
          newForm.querySelector('label abbr').remove();
          // Get all input elements within the container
          const inputElements = newForm.querySelectorAll("input");
          // Loop through each input element and remove the 'required' attribute
          inputElements.forEach((input) => {
            if (input.hasAttribute("required")) {
              input.removeAttribute("required");
            }
          });
        }

        // If the source element we're copying has an disabled delete button,
        // enable that button
        let deleteButton= newForm.querySelector('.delete-record');
        if (deleteButton.hasAttribute("disabled")) {
          deleteButton.removeAttribute("disabled");
        }
      }

      formNum++;

      newForm.innerHTML = newForm.innerHTML.replace(formNumberRegex, `${formIdentifier}-${formNum-1}-`);
      if (isOtherContactsForm) {
        // For the other contacts form, we need to update the fieldset headers based on what's visible vs hidden,
        // since the form on the backend employs Django's DELETE widget.
        let totalShownForms = document.querySelectorAll(`.repeatable-form:not([style*="display: none"])`).length;
        newForm.innerHTML = newForm.innerHTML.replace(formLabelRegex, `${formLabel} ${totalShownForms + 1}`);
      } else {
        // Nameservers form is cloned from index 2 which has the word optional on init, does not have the word optional
        // if indices 0 or 1 have been deleted
        let containsOptional = newForm.innerHTML.includes('(optional)');
        if (isNameserversForm && !containsOptional) {
          newForm.innerHTML = newForm.innerHTML.replace(formLabelRegex, `${formLabel} ${formNum} (optional)`);
        } else {
          newForm.innerHTML = newForm.innerHTML.replace(formLabelRegex, `${formLabel} ${formNum}`);
        }
      }
      newForm.innerHTML = newForm.innerHTML.replace(formExampleRegex, `ns${formNum}`);
      newForm.innerHTML = newForm.innerHTML.replace(/\n/g, '');  // Remove newline characters
      newForm.innerHTML = newForm.innerHTML.replace(/>\s*</g, '><');  // Remove spaces between tags
      container.insertBefore(newForm, addButton);

      newForm.style.display = 'block';

      let inputs = newForm.querySelectorAll("input");
      // Reset the values of each input to blank
      inputs.forEach((input) => {
        input.classList.remove("usa-input--error");
        input.classList.remove("usa-input--success");
        if (input.type === "text" || input.type === "number" || input.type === "password" || input.type === "email" || input.type === "tel") {
          input.value = ""; // Set the value to an empty string
          
        } else if (input.type === "checkbox" || input.type === "radio") {
          input.checked = false; // Uncheck checkboxes and radios
        }
      });

      // Reset any existing validation classes
      let selects = newForm.querySelectorAll("select");
      selects.forEach((select) => {
        select.classList.remove("usa-input--error");
        select.classList.remove("usa-input--success");
        select.selectedIndex = 0; // Set the value to an empty string
      });

      let labels = newForm.querySelectorAll("label");
      labels.forEach((label) => {
        label.classList.remove("usa-label--error");
        label.classList.remove("usa-label--success");
      });

      let usaFormGroups = newForm.querySelectorAll(".usa-form-group");
      usaFormGroups.forEach((usaFormGroup) => {
        usaFormGroup.classList.remove("usa-form-group--error");
        usaFormGroup.classList.remove("usa-form-group--success");
      });

      // Remove any existing error and success messages
      let usaMessages = newForm.querySelectorAll(".usa-error-message, .usa-alert");
      usaMessages.forEach((usaErrorMessage) => {
        let parentDiv = usaErrorMessage.closest('div');
        if (parentDiv) {
          parentDiv.remove(); // Remove the parent div if it exists
        }
      });

      totalForms.setAttribute('value', `${formNum}`);

      // Attach click event listener on the delete buttons of the new form
      let newDeleteButton = newForm.querySelector(".delete-record");
      if (newDeleteButton)
        prepareNewDeleteButton(newDeleteButton, formLabel);

      // Disable the add more button if we have 13 forms
      if (isNameserversForm && formNum == 13) {
        addButton.setAttribute("disabled", "true");
      }

      if (isNameserversForm && forms.length >= 2) {
        // Enable the delete buttons on the nameservers
        forms.forEach((form, index) => {
          Array.from(form.querySelectorAll('.delete-record')).forEach((deleteButton) => {
            deleteButton.removeAttribute("disabled");
          });
        });
      }
  }
})();

/**
 * An IIFE that triggers a modal on the DS Data Form under certain conditions
 *
 */
(function triggerModalOnDsDataForm() {
  let saveButon = document.querySelector("#save-ds-data");

  // The view context will cause a hitherto hidden modal trigger to
  // show up. On save, we'll test for that modal trigger appearing. We'll
  // run that test once every 100 ms for 5 secs, which should balance performance
  // while accounting for network or lag issues.
  if (saveButon) {
    let i = 0;
    var tryToTriggerModal = setInterval(function() {
        i++;
        if (i > 100) {
          clearInterval(tryToTriggerModal);
        }
        let modalTrigger = document.querySelector("#ds-toggle-dnssec-alert");
        if (modalTrigger) {
          modalTrigger.click()
          clearInterval(tryToTriggerModal);
        }
    }, 50);
  }
})();


/**
 * An IIFE that listens to the other contacts radio form on DAs and toggles the contacts/no other contacts forms 
 *
 */
(function otherContactsFormListener() {
  HookupYesNoListener("other_contacts-has_other_contacts",'other-employees', 'no-other-employees')
})();


/**
 * An IIFE that listens to the yes/no radio buttons on the anything else form and toggles form field visibility accordingly
 *
 */
(function anythingElseFormListener() {
  HookupYesNoListener("additional_details-has_anything_else_text",'anything-else', null)
})();


/**
 * An IIFE that listens to the yes/no radio buttons on the anything else form and toggles form field visibility accordingly
 *
 */
(function newMemberFormListener() {
  HookupRadioTogglerListener('member_access_level', {
          'admin': 'new-member-admin-permissions',
          'basic': 'new-member-basic-permissions'
        });
})();

/**
 * An IIFE that disables the delete buttons on nameserver forms on page load if < 3 forms
 *
 */
(function nameserversFormListener() {
  let isNameserversForm = document.querySelector(".nameservers-form");
  if (isNameserversForm) {
    let forms = document.querySelectorAll(".repeatable-form");
    if (forms.length < 3) {
      // Hide the delete buttons on the 2 nameservers
      forms.forEach((form) => {
        Array.from(form.querySelectorAll('.delete-record')).forEach((deleteButton) => {
          deleteButton.setAttribute("disabled", "true");
        });
      });
    }
  }
})();

/**
 * An IIFE that disables the delete buttons on nameserver forms on page load if < 3 forms
 *
 */
(function nameserversFormListener() {
  let isNameserversForm = document.querySelector(".nameservers-form");
  if (isNameserversForm) {
    let forms = document.querySelectorAll(".repeatable-form");
    if (forms.length < 3) {
      // Hide the delete buttons on the 2 nameservers
      forms.forEach((form) => {
        Array.from(form.querySelectorAll('.delete-record')).forEach((deleteButton) => {
          deleteButton.setAttribute("disabled", "true");
        });
      });
    }
  }
})();

/**
 * An IIFE that listens to the yes/no radio buttons on the CISA representatives form and toggles form field visibility accordingly
 *
 */
(function cisaRepresentativesFormListener() {
  HookupYesNoListener("additional_details-has_cisa_representative",'cisa-representative', null)
})();

/**
 * Initialize USWDS tooltips by calling initialization method.  Requires that uswds-edited.js
 * be loaded before get-gov.js.  uswds-edited.js adds the tooltip module to the window to be
 * accessible directly in get-gov.js
 * 
 */
function initializeTooltips() {
  function checkTooltip() {
    // Check that the tooltip library is loaded, and if not, wait and retry
    if (window.tooltip && typeof window.tooltip.init === 'function') {
        window.tooltip.init();
    } else {
        // Retry after a short delay
        setTimeout(checkTooltip, 100);
    }
  }
  checkTooltip();
}

/**
 * Initialize USWDS modals by calling on method.  Requires that uswds-edited.js be loaded
 * before get-gov.js.  uswds-edited.js adds the modal module to the window to be accessible
 * directly in get-gov.js.
 * initializeModals adds modal-related DOM elements, based on other DOM elements existing in 
 * the page.  It needs to be called only once for any particular DOM element; otherwise, it
 * will initialize improperly.  Therefore, if DOM elements change dynamically and include
 * DOM elements with modal classes, unloadModals needs to be called before initializeModals.
 * 
 */
function initializeModals() {
  window.modal.on();
}

/**
 * Unload existing USWDS modals by calling off method.  Requires that uswds-edited.js be
 * loaded before get-gov.js.  uswds-edited.js adds the modal module to the window to be
 * accessible directly in get-gov.js.
 * See note above with regards to calling this method relative to initializeModals.
 * 
 */
function unloadModals() {
  window.modal.off();
}

class LoadTableBase {
  constructor(sectionSelector) {
    this.tableWrapper = document.getElementById(`${sectionSelector}__table-wrapper`);
    this.tableHeaders = document.querySelectorAll(`#${sectionSelector} th[data-sortable]`);
    this.currentSortBy = 'id';
    this.currentOrder = 'asc';
    this.currentStatus = [];
    this.currentSearchTerm = '';
    this.scrollToTable = false;
    this.searchInput = document.getElementById(`${sectionSelector}__search-field`);
    this.searchSubmit = document.getElementById(`${sectionSelector}__search-field-submit`);
    this.tableAnnouncementRegion = document.getElementById(`${sectionSelector}__usa-table__announcement-region`);
    this.resetSearchButton = document.getElementById(`${sectionSelector}__reset-search`);
    this.resetFiltersButton = document.getElementById(`${sectionSelector}__reset-filters`);
    this.statusCheckboxes = document.querySelectorAll(`.${sectionSelector} input[name="filter-status"]`);
    this.statusIndicator = document.getElementById(`${sectionSelector}__filter-indicator`);
    this.statusToggle = document.getElementById(`${sectionSelector}__usa-button--filter`);
    this.noTableWrapper = document.getElementById(`${sectionSelector}__no-data`);
    this.noSearchResultsWrapper = document.getElementById(`${sectionSelector}__no-search-results`);
    this.portfolioElement = document.getElementById('portfolio-js-value');
    this.portfolioValue = this.portfolioElement ? this.portfolioElement.getAttribute('data-portfolio') : null;
    this.initializeTableHeaders();
    this.initializeSearchHandler();
    this.initializeStatusToggleHandler();
    this.initializeFilterCheckboxes();
    this.initializeResetSearchButton();
    this.initializeResetFiltersButton();
    this.initializeAccordionAccessibilityListeners();
  }

  /**
 * Generalized function to update pagination for a list.
 * @param {string} itemName - The name displayed in the counter
 * @param {string} paginationSelector - CSS selector for the pagination container.
 * @param {string} counterSelector - CSS selector for the pagination counter.
 * @param {string} tableSelector - CSS selector for the header element to anchor the links to.
 * @param {number} currentPage - The current page number (starting with 1).
 * @param {number} numPages - The total number of pages.
 * @param {boolean} hasPrevious - Whether there is a page before the current page.
 * @param {boolean} hasNext - Whether there is a page after the current page.
 * @param {number} total - The total number of items.
 */  
  updatePagination(
    itemName,
    paginationSelector,
    counterSelector,
    parentTableSelector,
    currentPage,
    numPages,
    hasPrevious,
    hasNext,
    totalItems,
  ) {
    const paginationButtons = document.querySelector(`${paginationSelector} .usa-pagination__list`);
    const counterSelectorEl = document.querySelector(counterSelector);
    const paginationSelectorEl = document.querySelector(paginationSelector);
    counterSelectorEl.innerHTML = '';
    paginationButtons.innerHTML = '';

    // Buttons should only be displayed if there are more than one pages of results
    paginationButtons.classList.toggle('display-none', numPages <= 1);

    // Counter should only be displayed if there is more than 1 item
    paginationSelectorEl.classList.toggle('display-none', totalItems < 1);

    counterSelectorEl.innerHTML = `${totalItems} ${itemName}${totalItems > 1 ? 's' : ''}${this.currentSearchTerm ? ' for ' + '"' + this.currentSearchTerm + '"' : ''}`;

    if (hasPrevious) {
      const prevPageItem = document.createElement('li');
      prevPageItem.className = 'usa-pagination__item usa-pagination__arrow';
      prevPageItem.innerHTML = `
        <a href="${parentTableSelector}" class="usa-pagination__link usa-pagination__previous-page" aria-label="Previous page">
          <svg class="usa-icon" aria-hidden="true" role="img">
            <use xlink:href="/public/img/sprite.svg#navigate_before"></use>
          </svg>
          <span class="usa-pagination__link-text">Previous</span>
        </a>
      `;
      prevPageItem.querySelector('a').addEventListener('click', (event) => {
        event.preventDefault();
        this.loadTable(currentPage - 1);
      });
      paginationButtons.appendChild(prevPageItem);
    }

    // Add first page and ellipsis if necessary
    if (currentPage > 2) {
      paginationButtons.appendChild(this.createPageItem(1, parentTableSelector, currentPage));
      if (currentPage > 3) {
        const ellipsis = document.createElement('li');
        ellipsis.className = 'usa-pagination__item usa-pagination__overflow';
        ellipsis.setAttribute('aria-label', 'ellipsis indicating non-visible pages');
        ellipsis.innerHTML = '<span>…</span>';
        paginationButtons.appendChild(ellipsis);
      }
    }

    // Add pages around the current page
    for (let i = Math.max(1, currentPage - 1); i <= Math.min(numPages, currentPage + 1); i++) {
      paginationButtons.appendChild(this.createPageItem(i, parentTableSelector, currentPage));
    }

    // Add last page and ellipsis if necessary
    if (currentPage < numPages - 1) {
      if (currentPage < numPages - 2) {
        const ellipsis = document.createElement('li');
        ellipsis.className = 'usa-pagination__item usa-pagination__overflow';
        ellipsis.setAttribute('aria-label', 'ellipsis indicating non-visible pages');
        ellipsis.innerHTML = '<span>…</span>';
        paginationButtons.appendChild(ellipsis);
      }
      paginationButtons.appendChild(this.createPageItem(numPages, parentTableSelector, currentPage));
    }

    if (hasNext) {
      const nextPageItem = document.createElement('li');
      nextPageItem.className = 'usa-pagination__item usa-pagination__arrow';
      nextPageItem.innerHTML = `
        <a href="${parentTableSelector}" class="usa-pagination__link usa-pagination__next-page" aria-label="Next page">
          <span class="usa-pagination__link-text">Next</span>
          <svg class="usa-icon" aria-hidden="true" role="img">
            <use xlink:href="/public/img/sprite.svg#navigate_next"></use>
          </svg>
        </a>
      `;
      nextPageItem.querySelector('a').addEventListener('click', (event) => {
        event.preventDefault();
        this.loadTable(currentPage + 1);
      });
      paginationButtons.appendChild(nextPageItem);
    }
  }

  /**
   * A helper that toggles content/ no content/ no search results
   *
  */
  updateDisplay = (data, dataWrapper, noDataWrapper, noSearchResultsWrapper) => {
    const { unfiltered_total, total } = data;
    if (unfiltered_total) {
      if (total) {
        showElement(dataWrapper);
        hideElement(noSearchResultsWrapper);
        hideElement(noDataWrapper);
      } else {
        hideElement(dataWrapper);
        showElement(noSearchResultsWrapper);
        hideElement(noDataWrapper);
      }
    } else {
      hideElement(dataWrapper);
      hideElement(noSearchResultsWrapper);
      showElement(noDataWrapper);
    }
  };

  // Helper function to create a page item
  createPageItem(page, parentTableSelector, currentPage) {
    const pageItem = document.createElement('li');
    pageItem.className = 'usa-pagination__item usa-pagination__page-no';
    pageItem.innerHTML = `
      <a href="${parentTableSelector}" class="usa-pagination__button" aria-label="Page ${page}">${page}</a>
    `;
    if (page === currentPage) {
      pageItem.querySelector('a').classList.add('usa-current');
      pageItem.querySelector('a').setAttribute('aria-current', 'page');
    }
    pageItem.querySelector('a').addEventListener('click', (event) => {
      event.preventDefault();
      this.loadTable(page);
    });
    return pageItem;
  }

  /**
   * A helper that resets sortable table headers
   *
  */
  unsetHeader = (header) => {
    header.removeAttribute('aria-sort');
    let headerName = header.innerText;
    const headerLabel = `${headerName}, sortable column, currently unsorted"`;
    const headerButtonLabel = `Click to sort by ascending order.`;
    header.setAttribute("aria-label", headerLabel);
    header.querySelector('.usa-table__header__button').setAttribute("title", headerButtonLabel);
  };

  // Abstract method (to be implemented in the child class)
  loadTable(page, sortBy, order) {
    throw new Error('loadData() must be implemented in a subclass');
  }

  // Add event listeners to table headers for sorting
  initializeTableHeaders() {
    this.tableHeaders.forEach(header => {
      header.addEventListener('click', () => {
        const sortBy = header.getAttribute('data-sortable');
        let order = 'asc';
        // sort order will be ascending, unless the currently sorted column is ascending, and the user
        // is selecting the same column to sort in descending order
        if (sortBy === this.currentSortBy) {
          order = this.currentOrder === 'asc' ? 'desc' : 'asc';
        }
        // load the results with the updated sort
        this.loadTable(1, sortBy, order);
      });
    });
  }

  initializeSearchHandler() {
    this.searchSubmit.addEventListener('click', (e) => {
      e.preventDefault();
      this.currentSearchTerm = this.searchInput.value;
      // If the search is blank, we match the resetSearch functionality
      if (this.currentSearchTerm) {
        showElement(this.resetSearchButton);
      } else {
        hideElement(this.resetSearchButton);
      }
      this.loadTable(1, 'id', 'asc');
      this.resetHeaders();
    });
  }

  initializeStatusToggleHandler() {
    if (this.statusToggle) {
      this.statusToggle.addEventListener('click', () => {
        toggleCaret(this.statusToggle);
      });
    }
  }

  // Add event listeners to status filter checkboxes
  initializeFilterCheckboxes() {
    this.statusCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        const checkboxValue = checkbox.value;
        
        // Update currentStatus array based on checkbox state
        if (checkbox.checked) {
          this.currentStatus.push(checkboxValue);
        } else {
          const index = this.currentStatus.indexOf(checkboxValue);
          if (index > -1) {
            this.currentStatus.splice(index, 1);
          }
        }

        // Manage visibility of reset filters button
        if (this.currentStatus.length == 0) {
          hideElement(this.resetFiltersButton);
        } else {
          showElement(this.resetFiltersButton);
        }

        // Disable the auto scroll
        this.scrollToTable = false;

        // Call loadTable with updated status
        this.loadTable(1, 'id', 'asc');
        this.resetHeaders();
        this.updateStatusIndicator();
      });
    });
  }

  // Reset UI and accessibility
  resetHeaders() {
    this.tableHeaders.forEach(header => {
      // Unset sort UI in headers
      this.unsetHeader(header);
    });
    // Reset the announcement region
    this.tableAnnouncementRegion.innerHTML = '';
  }

  resetSearch() {
    this.searchInput.value = '';
    this.currentSearchTerm = '';
    hideElement(this.resetSearchButton);
    this.loadTable(1, 'id', 'asc');
    this.resetHeaders();
  }

  initializeResetSearchButton() {
    if (this.resetSearchButton) {
      this.resetSearchButton.addEventListener('click', () => {
        this.resetSearch();
      });
    }
  }

  resetFilters() {
    this.currentStatus = [];
    this.statusCheckboxes.forEach(checkbox => {
      checkbox.checked = false; 
    });
    hideElement(this.resetFiltersButton);

    // Disable the auto scroll
    this.scrollToTable = false;

    this.loadTable(1, 'id', 'asc');
    this.resetHeaders();
    this.updateStatusIndicator();
    // No need to toggle close the filters. The focus shift will trigger that for us.
  }

  initializeResetFiltersButton() {
    if (this.resetFiltersButton) {
      this.resetFiltersButton.addEventListener('click', () => {
        this.resetFilters();
      });
    }
  }

  updateStatusIndicator() {
    this.statusIndicator.innerHTML = '';
    // Even if the element is empty, it'll mess up the flex layout unless we set display none
    hideElement(this.statusIndicator);
    if (this.currentStatus.length)
      this.statusIndicator.innerHTML = '(' + this.currentStatus.length + ')';
      showElement(this.statusIndicator);
  }

  closeFilters() {
    if (this.statusToggle.getAttribute("aria-expanded") === "true") {
      this.statusToggle.click();
    }
  }

  initializeAccordionAccessibilityListeners() {
    // Instead of managing the toggle/close on the filter buttons in all edge cases (user clicks on search, user clicks on ANOTHER filter,
    // user clicks on main nav...) we add a listener and close the filters whenever the focus shifts out of the dropdown menu/filter button.
    // NOTE: We may need to evolve this as we add more filters.
    document.addEventListener('focusin', (event) => {
      const accordion = document.querySelector('.usa-accordion--select');
      const accordionThatIsOpen = document.querySelector('.usa-button--filter[aria-expanded="true"]');
      
      if (accordionThatIsOpen && !accordion.contains(event.target)) {
        this.closeFilters();
      }
    });

    // Close when user clicks outside
    // NOTE: We may need to evolve this as we add more filters.
    document.addEventListener('click', (event) => {
      const accordion = document.querySelector('.usa-accordion--select');
      const accordionThatIsOpen = document.querySelector('.usa-button--filter[aria-expanded="true"]');
    
      if (accordionThatIsOpen && !accordion.contains(event.target)) {
        this.closeFilters();
      }
    });
  }
}

class DomainsTable extends LoadTableBase {

  constructor() {
    super('domains');
  }
  /**
     * Loads rows in the domains list, as well as updates pagination around the domains list
     * based on the supplied attributes.
     * @param {*} page - the page number of the results (starts with 1)
     * @param {*} sortBy - the sort column option
     * @param {*} order - the sort order {asc, desc}
     * @param {*} scroll - control for the scrollToElement functionality
     * @param {*} status - control for the status filter
     * @param {*} searchTerm - the search term
     * @param {*} portfolio - the portfolio id
     */
  loadTable(page, sortBy = this.currentSortBy, order = this.currentOrder, scroll = this.scrollToTable, status = this.currentStatus, searchTerm =this.currentSearchTerm, portfolio = this.portfolioValue) {

      // fetch json of page of domais, given params
      let baseUrl = document.getElementById("get_domains_json_url");
      if (!baseUrl) {
        return;
      }

      let baseUrlValue = baseUrl.innerHTML;
      if (!baseUrlValue) {
        return;
      }

      // fetch json of page of domains, given params
      let searchParams = new URLSearchParams(
        {
          "page": page,
          "sort_by": sortBy,
          "order": order,
          "status": status,
          "search_term": searchTerm
        }
      );
      if (portfolio)
        searchParams.append("portfolio", portfolio)

      let url = `${baseUrlValue}?${searchParams.toString()}`
      fetch(url)
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error('Error in AJAX call: ' + data.error);
            return;
          }

          // handle the display of proper messaging in the event that no domains exist in the list or search returns no results
          this.updateDisplay(data, this.tableWrapper, this.noTableWrapper, this.noSearchResultsWrapper, this.currentSearchTerm);

          // identify the DOM element where the domain list will be inserted into the DOM
          const domainList = document.querySelector('#domains tbody');
          domainList.innerHTML = '';

          data.domains.forEach(domain => {
            const options = { year: 'numeric', month: 'short', day: 'numeric' };
            const expirationDate = domain.expiration_date ? new Date(domain.expiration_date) : null;
            const expirationDateFormatted = expirationDate ? expirationDate.toLocaleDateString('en-US', options) : '';
            const expirationDateSortValue = expirationDate ? expirationDate.getTime() : '';
            const actionUrl = domain.action_url;
            const suborganization = domain.domain_info__sub_organization ? domain.domain_info__sub_organization : '⎯';

            const row = document.createElement('tr');

            let markupForSuborganizationRow = '';

            if (this.portfolioValue) {
              markupForSuborganizationRow = `
                <td>
                    <span class="text-wrap" aria-label="${domain.suborganization ? suborganization : 'No suborganization'}">${suborganization}</span>
                </td>
              `
            }

            row.innerHTML = `
              <th scope="row" role="rowheader" data-label="Domain name">
                ${domain.name}
              </th>
              <td data-sort-value="${expirationDateSortValue}" data-label="Expires">
                ${expirationDateFormatted}
              </td>
              <td data-label="Status">
                ${domain.state_display}
                <svg 
                  class="usa-icon usa-tooltip usa-tooltip--registrar text-middle margin-bottom-05 text-accent-cool no-click-outline-and-cursor-help" 
                  data-position="top"
                  title="${domain.get_state_help_text}"
                  focusable="true"
                  aria-label="${domain.get_state_help_text}"
                  role="tooltip"
                >
                  <use aria-hidden="true" xlink:href="/public/img/sprite.svg#info_outline"></use>
                </svg>
              </td>
              ${markupForSuborganizationRow}
              <td>
                <a href="${actionUrl}">
                  <svg class="usa-icon" aria-hidden="true" focusable="false" role="img" width="24">
                    <use xlink:href="/public/img/sprite.svg#${domain.svg_icon}"></use>
                  </svg>
                  ${domain.action_label} <span class="usa-sr-only">${domain.name}</span>
                </a>
              </td>
            `;
            domainList.appendChild(row);
          });
          // initialize tool tips immediately after the associated DOM elements are added
          initializeTooltips();

          // Do not scroll on first page load
          if (scroll)
            ScrollToElement('class', 'domains');
          this.scrollToTable = true;

          // update pagination
          this.updatePagination(
            'domain',
            '#domains-pagination',
            '#domains-pagination .usa-pagination__counter',
            '#domains',
            data.page,
            data.num_pages,
            data.has_previous,
            data.has_next,
            data.total,
          );
          this.currentSortBy = sortBy;
          this.currentOrder = order;
          this.currentSearchTerm = searchTerm;
        })
        .catch(error => console.error('Error fetching domains:', error));
  }
}

class DomainRequestsTable extends LoadTableBase {

  constructor() {
    super('domain-requests');
  }
  
  toggleExportButton(requests) {
    const exportButton = document.getElementById('export-csv'); 
    if (exportButton) {
        if (requests.length > 0) {
            showElement(exportButton);
        } else {
            hideElement(exportButton);
        }
    }
}

  /**
     * Loads rows in the domains list, as well as updates pagination around the domains list
     * based on the supplied attributes.
     * @param {*} page - the page number of the results (starts with 1)
     * @param {*} sortBy - the sort column option
     * @param {*} order - the sort order {asc, desc}
     * @param {*} scroll - control for the scrollToElement functionality
     * @param {*} status - control for the status filter
     * @param {*} searchTerm - the search term
     * @param {*} portfolio - the portfolio id
     */
  loadTable(page, sortBy = this.currentSortBy, order = this.currentOrder, scroll = this.scrollToTable, status = this.currentStatus, searchTerm = this.currentSearchTerm, portfolio = this.portfolioValue) {
    let baseUrl = document.getElementById("get_domain_requests_json_url");
    
    if (!baseUrl) {
      return;
    }

    let baseUrlValue = baseUrl.innerHTML;
    if (!baseUrlValue) {
      return;
    }

    // add searchParams
    let searchParams = new URLSearchParams(
      {
        "page": page,
        "sort_by": sortBy,
        "order": order,
        "status": status,
        "search_term": searchTerm
      }
    );
    if (portfolio)
      searchParams.append("portfolio", portfolio)

    let url = `${baseUrlValue}?${searchParams.toString()}`
    fetch(url)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          console.error('Error in AJAX call: ' + data.error);
          return;
        }

        // Manage "export as CSV" visibility for domain requests
        this.toggleExportButton(data.domain_requests);

        // handle the display of proper messaging in the event that no requests exist in the list or search returns no results
        this.updateDisplay(data, this.tableWrapper, this.noTableWrapper, this.noSearchResultsWrapper, this.currentSearchTerm);

        // identify the DOM element where the domain request list will be inserted into the DOM
        const tbody = document.querySelector('#domain-requests tbody');
        tbody.innerHTML = '';

        // Unload modals will re-inject the DOM with the initial placeholders to allow for .on() in regular use cases
        // We do NOT want that as it will cause multiple placeholders and therefore multiple inits on delete,
        // which will cause bad delete requests to be sent.
        const preExistingModalPlaceholders = document.querySelectorAll('[data-placeholder-for^="toggle-delete-domain-alert"]');
        preExistingModalPlaceholders.forEach(element => {
            element.remove();
        });

        // remove any existing modal elements from the DOM so they can be properly re-initialized
        // after the DOM content changes and there are new delete modal buttons added
        unloadModals();

        let needsDeleteColumn = false;

        needsDeleteColumn = data.domain_requests.some(request => request.is_deletable);

        // Remove existing delete th and td if they exist
        let existingDeleteTh =  document.querySelector('.delete-header');
        if (!needsDeleteColumn) {
          if (existingDeleteTh)
            existingDeleteTh.remove();
        } else {
          if (!existingDeleteTh) {
            const delheader = document.createElement('th');
            delheader.setAttribute('scope', 'col');
            delheader.setAttribute('role', 'columnheader');
            delheader.setAttribute('class', 'delete-header');
            delheader.innerHTML = `
              <span class="usa-sr-only">Delete Action</span>`;
            let tableHeaderRow = document.querySelector('#domain-requests thead tr');
            tableHeaderRow.appendChild(delheader);
          }
        }

        data.domain_requests.forEach(request => {
          const options = { year: 'numeric', month: 'short', day: 'numeric' };
          const domainName = request.requested_domain ? request.requested_domain : `New domain request <br><span class="text-base font-body-xs">(${utcDateString(request.created_at)})</span>`;
          const actionUrl = request.action_url;
          const actionLabel = request.action_label;
          const submissionDate = request.last_submitted_date ? new Date(request.last_submitted_date).toLocaleDateString('en-US', options) : `<span class="text-base">Not submitted</span>`;
          
          // The markup for the delete function either be a simple trigger or a 3 dots menu with a hidden trigger (in the case of portfolio requests page)
          // If the request is not deletable, use the following (hidden) span for ANDI screenreaders to indicate this state to the end user
          let modalTrigger =  `
          <span class="usa-sr-only">Domain request cannot be deleted now. Edit the request for more information.</span>`;

          let markupCreatorRow = '';

          if (this.portfolioValue) {
            markupCreatorRow = `
              <td>
                  <span class="text-wrap break-word">${request.creator ? request.creator : ''}</span>
              </td>
            `
          }

          if (request.is_deletable) {
            // If the request is deletable, create modal body and insert it. This is true for both requests and portfolio requests pages
            let modalHeading = '';
            let modalDescription = '';

            if (request.requested_domain) {
              modalHeading = `Are you sure you want to delete ${request.requested_domain}?`;
              modalDescription = 'This will remove the domain request from the .gov registrar. This action cannot be undone.';
            } else {
              if (request.created_at) {
                modalHeading = 'Are you sure you want to delete this domain request?';
                modalDescription = `This will remove the domain request (created ${utcDateString(request.created_at)}) from the .gov registrar. This action cannot be undone`;
              } else {
                modalHeading = 'Are you sure you want to delete New domain request?';
                modalDescription = 'This will remove the domain request from the .gov registrar. This action cannot be undone.';
              }
            }

            modalTrigger = `
              <a 
                role="button" 
                id="button-toggle-delete-domain-alert-${request.id}"
                href="#toggle-delete-domain-alert-${request.id}"
                class="usa-button text-secondary usa-button--unstyled text-no-underline late-loading-modal-trigger line-height-sans-5"
                aria-controls="toggle-delete-domain-alert-${request.id}"
                data-open-modal
              >
                <svg class="usa-icon" aria-hidden="true" focusable="false" role="img" width="24">
                  <use xlink:href="/public/img/sprite.svg#delete"></use>
                </svg> Delete <span class="usa-sr-only">${domainName}</span>
              </a>`

            const modalSubmit = `
              <button type="button"
              class="usa-button usa-button--secondary usa-modal__submit"
              data-pk = ${request.id}
              name="delete-domain-request">Yes, delete request</button>
            `

            const modal = document.createElement('div');
            modal.setAttribute('class', 'usa-modal');
            modal.setAttribute('id', `toggle-delete-domain-alert-${request.id}`);
            modal.setAttribute('aria-labelledby', 'Are you sure you want to continue?');
            modal.setAttribute('aria-describedby', 'Domain will be removed');
            modal.setAttribute('data-force-action', '');

            modal.innerHTML = `
              <div class="usa-modal__content">
                <div class="usa-modal__main">
                  <h2 class="usa-modal__heading" id="modal-1-heading">
                    ${modalHeading}
                  </h2>
                  <div class="usa-prose">
                    <p id="modal-1-description">
                      ${modalDescription}
                    </p>
                  </div>
                  <div class="usa-modal__footer">
                      <ul class="usa-button-group">
                        <li class="usa-button-group__item">
                          ${modalSubmit}
                        </li>      
                        <li class="usa-button-group__item">
                            <button
                                type="button"
                                class="usa-button usa-button--unstyled padding-105 text-center"
                                data-close-modal
                            >
                                Cancel
                            </button>
                        </li>
                      </ul>
                  </div>
                </div>
                <button
                  type="button"
                  class="usa-button usa-modal__close"
                  aria-label="Close this window"
                  data-close-modal
                >
                  <svg class="usa-icon" aria-hidden="true" focusable="false" role="img">
                    <use xlink:href="/public/img/sprite.svg#close"></use>
                  </svg>
                </button>
              </div>
              `

            this.tableWrapper.appendChild(modal);

            // Request is deletable, modal and modalTrigger are built. Now check if we are on the portfolio requests page (by seeing if there is a portfolio value) and enhance the modalTrigger accordingly
            if (this.portfolioValue) {
              modalTrigger = `
              <a 
                role="button" 
                id="button-toggle-delete-domain-alert-${request.id}"
                href="#toggle-delete-domain-alert-${request.id}"
                class="usa-button text-secondary usa-button--unstyled text-no-underline late-loading-modal-trigger margin-top-2 visible-mobile-flex line-height-sans-5"
                aria-controls="toggle-delete-domain-alert-${request.id}"
                data-open-modal
              >
                <svg class="usa-icon" aria-hidden="true" focusable="false" role="img" width="24">
                  <use xlink:href="/public/img/sprite.svg#delete"></use>
                </svg> Delete <span class="usa-sr-only">${domainName}</span>
              </a>

              <div class="usa-accordion usa-accordion--more-actions margin-right-2 hidden-mobile-flex">
                <div class="usa-accordion__heading">
                  <button
                    type="button"
                    class="usa-button usa-button--unstyled usa-button--with-icon usa-accordion__button usa-button--more-actions"
                    aria-expanded="false"
                    aria-controls="more-actions-${request.id}"
                  >
                    <svg class="usa-icon top-2px" aria-hidden="true" focusable="false" role="img" width="24">
                      <use xlink:href="/public/img/sprite.svg#more_vert"></use>
                    </svg>
                  </button>
                </div>
                <div id="more-actions-${request.id}" class="usa-accordion__content usa-prose shadow-1 left-auto right-0" hidden>
                  <h2>More options</h2>
                  <a 
                    role="button" 
                    id="button-toggle-delete-domain-alert-${request.id}"
                    href="#toggle-delete-domain-alert-${request.id}"
                    class="usa-button text-secondary usa-button--unstyled text-no-underline late-loading-modal-trigger margin-top-2 line-height-sans-5"
                    aria-controls="toggle-delete-domain-alert-${request.id}"
                    data-open-modal
                  >
                    <svg class="usa-icon" aria-hidden="true" focusable="false" role="img" width="24">
                      <use xlink:href="/public/img/sprite.svg#delete"></use>
                    </svg> Delete <span class="usa-sr-only">${domainName}</span>
                  </a>
                </div>
              </div>
              `
            }
          }


          const row = document.createElement('tr');
          row.innerHTML = `
            <th scope="row" role="rowheader" data-label="Domain name">
              ${domainName}
            </th>
            <td data-sort-value="${new Date(request.last_submitted_date).getTime()}" data-label="Date submitted">
              ${submissionDate}
            </td>
            ${markupCreatorRow}
            <td data-label="Status">
              ${request.status}
            </td>
            <td>
              <a href="${actionUrl}">
                <svg class="usa-icon" aria-hidden="true" focusable="false" role="img" width="24">
                  <use xlink:href="/public/img/sprite.svg#${request.svg_icon}"></use>
                </svg>
                ${actionLabel} <span class="usa-sr-only">${request.requested_domain ? request.requested_domain : 'New domain request'}</span>
              </a>
            </td>
            ${needsDeleteColumn ? '<td>'+modalTrigger+'</td>' : ''}
          `;
          tbody.appendChild(row);
        });

        // initialize modals immediately after the DOM content is updated
        initializeModals();

        // Now the DOM and modals are ready, add listeners to the submit buttons
        const modals = document.querySelectorAll('.usa-modal__content');

        modals.forEach(modal => {
          const submitButton = modal.querySelector('.usa-modal__submit');
          const closeButton = modal.querySelector('.usa-modal__close');
          submitButton.addEventListener('click', () => {
            let pk = submitButton.getAttribute('data-pk');
            // Close the modal to remove the USWDS UI local classes
            closeButton.click();
            // If we're deleting the last item on a page that is not page 1, we'll need to refresh the display to the previous page
            let pageToDisplay = data.page;
            if (data.total == 1 && data.unfiltered_total > 1) {
              pageToDisplay--;
            }
            this.deleteDomainRequest(pk, pageToDisplay);
          });
        });

        // Do not scroll on first page load
        if (scroll)
          ScrollToElement('class', 'domain-requests');
        this.scrollToTable = true;

        // update the pagination after the domain requests list is updated
        this.updatePagination(
          'domain request',
          '#domain-requests-pagination',
          '#domain-requests-pagination .usa-pagination__counter',
          '#domain-requests',
          data.page,
          data.num_pages,
          data.has_previous,
          data.has_next,
          data.total,
        );
        this.currentSortBy = sortBy;
        this.currentOrder = order;
        this.currentSearchTerm = searchTerm;
      })
      .catch(error => console.error('Error fetching domain requests:', error));
  }

  /**
   * Delete is actually a POST API that requires a csrf token. The token will be waiting for us in the template as a hidden input.
   * @param {*} domainRequestPk - the identifier for the request that we're deleting
   * @param {*} pageToDisplay - If we're deleting the last item on a page that is not page 1, we'll need to display the previous page
  */
  deleteDomainRequest(domainRequestPk, pageToDisplay) {
    // Use to debug uswds modal issues
    //console.log('deleteDomainRequest')
    
    // Get csrf token
    const csrfToken = getCsrfToken();
    // Create FormData object and append the CSRF token
    const formData = `csrfmiddlewaretoken=${encodeURIComponent(csrfToken)}&delete-domain-request=`;

    fetch(`/domain-request/${domainRequestPk}/delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrfToken,
      },
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      // Update data and UI
      this.loadTable(pageToDisplay, this.currentSortBy, this.currentOrder, this.scrollToTable, this.currentSearchTerm);
    })
    .catch(error => console.error('Error fetching domain requests:', error));
  }
}

class MembersTable extends LoadTableBase {

  constructor() {
    super('members');
  }
  
  /**
   * Initializes "Show More" buttons on the page, enabling toggle functionality to show or hide content.
   * 
   * The function finds elements with "Show More" buttons and sets up a click event listener to toggle the visibility
   * of a corresponding content div. When clicked, the button updates its visual state (e.g., text/icon change),
   * and the associated content is shown or hidden based on its current visibility status.
   *
   * @function initShowMoreButtons
   */
  initShowMoreButtons() {
    /**
     * Toggles the visibility of a content section when the "Show More" button is clicked.
     * Updates the button text/icon based on whether the content is shown or hidden.
     *
     * @param {HTMLElement} toggleButton - The button that toggles the content visibility.
     * @param {HTMLElement} contentDiv - The content div whose visibility is toggled.
     * @param {HTMLElement} buttonParentRow - The parent row element containing the button.
     */
    function toggleShowMoreButton(toggleButton, contentDiv, buttonParentRow) {
      const spanElement = toggleButton.querySelector('span');
      const useElement = toggleButton.querySelector('use');
      if (contentDiv.classList.contains('display-none')) {
        showElement(contentDiv);
        spanElement.textContent = 'Close';
        useElement.setAttribute('xlink:href', '/public/img/sprite.svg#expand_less');
        buttonParentRow.classList.add('hide-td-borders');
        toggleButton.setAttribute('aria-label', 'Close additional information');
      } else {    
        hideElement(contentDiv);
        spanElement.textContent = 'Expand';
        useElement.setAttribute('xlink:href', '/public/img/sprite.svg#expand_more');
        buttonParentRow.classList.remove('hide-td-borders');
        toggleButton.setAttribute('aria-label', 'Expand for additional information');
      }
    }
  
    let toggleButtons = document.querySelectorAll('.usa-button--show-more-button');
    toggleButtons.forEach((toggleButton) => {
      
      // get contentDiv for element specified in data-for attribute of toggleButton
      let dataFor = toggleButton.dataset.for;
      let contentDiv = document.getElementById(dataFor);
      let buttonParentRow = toggleButton.parentElement.parentElement;
      if (contentDiv && contentDiv.tagName.toLowerCase() === 'tr' && contentDiv.classList.contains('show-more-content') && buttonParentRow && buttonParentRow.tagName.toLowerCase() === 'tr') {
        toggleButton.addEventListener('click', function() {
          toggleShowMoreButton(toggleButton, contentDiv, buttonParentRow);
        });
      } else {
        console.warn('Found a toggle button with no associated toggleable content or parent row');
      }

    });
  }

  /**
   * Converts a given `last_active` value into a display value and a numeric sort value.
   * The input can be a UTC date, the strings "Invited", "Invalid date", or null/undefined.
   * 
   * @param {string} last_active - UTC date string or special status like "Invited" or "Invalid date".
   * @returns {Object} - An object containing `display_value` (formatted date or status string) 
   *                     and `sort_value` (numeric value for sorting).
   */
  handleLastActive(last_active) {
    const invited = 'Invited';
    const invalid_date = 'Invalid date';
    const options = { year: 'numeric', month: 'long', day: 'numeric' }; // Date display format

    let display_value = invalid_date; // Default display value for invalid or null dates
    let sort_value = -1;              // Default sort value for invalid or null dates

    if (last_active === invited) {
      // Handle "Invited" status: special case with 0 sort value
      display_value = invited;
      sort_value = 0;
    } else if (last_active && last_active !== invalid_date) {
      // Parse and format valid UTC date strings
      const parsedDate = new Date(last_active);

      if (!isNaN(parsedDate.getTime())) {
        // Valid date
        display_value = parsedDate.toLocaleDateString('en-US', options);
        sort_value = parsedDate.getTime(); // Use timestamp for sorting
      } else {
        console.error(`Error: Invalid date string provided: ${last_active}`);
      }
    }

    return { display_value, sort_value };
  }

  /**
   * Generates HTML for the list of domains assigned to a member.
   * 
   * @param {number} num_domains - The number of domains the member is assigned to.
   * @param {Array} domain_names - An array of domain names.
   * @param {Array} domain_urls - An array of corresponding domain URLs.
   * @returns {string} - A string of HTML displaying the domains assigned to the member.
   */
  generateDomainsHTML(num_domains, domain_names, domain_urls, action_url) {
    // Initialize an empty string for the HTML
    let domainsHTML = '';

    // Only generate HTML if the member has one or more assigned domains
    if (num_domains > 0) {
      domainsHTML += "<div class='desktop:grid-col-5 margin-bottom-2 desktop:margin-bottom-0'>";
      domainsHTML += "<h4 class='margin-y-0 text-primary'>Domains assigned</h4>";
      domainsHTML += `<p class='margin-y-0'>This member is assigned to ${num_domains} domains:</p>`;
      domainsHTML += "<ul class='usa-list usa-list--unstyled margin-y-0'>";

      // Display up to 6 domains with their URLs
      for (let i = 0; i < num_domains && i < 6; i++) {
        domainsHTML += `<li><a href="${domain_urls[i]}">${domain_names[i]}</a></li>`;
      }

      domainsHTML += "</ul>";

      // If there are more than 6 domains, display a "View assigned domains" link
      if (num_domains >= 6) {
        domainsHTML += `<p><a href="${action_url}/domains">View assigned domains</a></p>`;
      }

      domainsHTML += "</div>";
    }

    return domainsHTML;
  }

  /**
   * Generates an HTML string summarizing a user's additional permissions within a portfolio, 
   * based on the user's permissions and predefined permission choices.
   *
   * @param {Array} member_permissions - An array of permission strings that the member has.
   * @param {Object} UserPortfolioPermissionChoices - An object containing predefined permission choice constants.
   *        Expected keys include:
   *        - VIEW_ALL_DOMAINS
   *        - VIEW_MANAGED_DOMAINS
   *        - EDIT_REQUESTS
   *        - VIEW_ALL_REQUESTS
   *        - EDIT_MEMBERS
   *        - VIEW_MEMBERS
   * 
   * @returns {string} - A string of HTML representing the user's additional permissions.
   *                     If the user has no specific permissions, it returns a default message
   *                     indicating no additional permissions.
   *
   * Behavior:
   * - The function checks the user's permissions (`member_permissions`) and generates
   *   corresponding HTML sections based on the permission choices defined in `UserPortfolioPermissionChoices`.
   * - Permissions are categorized into domains, requests, and members:
   *   - Domains: Determines whether the user can view or manage all or assigned domains.
   *   - Requests: Differentiates between users who can edit requests, view all requests, or have no request privileges.
   *   - Members: Distinguishes between members who can manage or only view other members.
   * - If no relevant permissions are found, the function returns a message stating that the user has no additional permissions.
   * - The resulting HTML always includes a header "Additional permissions for this member" and appends the relevant permission descriptions.
   */
  generatePermissionsHTML(member_permissions, UserPortfolioPermissionChoices) {
    let permissionsHTML = '';

    // Check domain-related permissions
    if (member_permissions.includes(UserPortfolioPermissionChoices.VIEW_ALL_DOMAINS)) {
      permissionsHTML += "<p class='margin-top-1 p--blockquote'><strong class='text-base-dark'>Domains:</strong> Can view all organization domains. Can manage domains they are assigned to and edit information about the domain (including DNS settings).</p>";
    } else if (member_permissions.includes(UserPortfolioPermissionChoices.VIEW_MANAGED_DOMAINS)) {
      permissionsHTML += "<p class='margin-top-1 p--blockquote'><strong class='text-base-dark'>Domains:</strong> Can manage domains they are assigned to and edit information about the domain (including DNS settings).</p>";
    }

    // Check request-related permissions
    if (member_permissions.includes(UserPortfolioPermissionChoices.EDIT_REQUESTS)) {
      permissionsHTML += "<p class='margin-top-1 p--blockquote'><strong class='text-base-dark'>Domain requests:</strong> Can view all organization domain requests. Can create domain requests and modify their own requests.</p>";
    } else if (member_permissions.includes(UserPortfolioPermissionChoices.VIEW_ALL_REQUESTS)) {
      permissionsHTML += "<p class='margin-top-1 p--blockquote'><strong class='text-base-dark'>Domain requests (view-only):</strong> Can view all organization domain requests. Can't create or modify any domain requests.</p>";
    }

    // Check member-related permissions
    if (member_permissions.includes(UserPortfolioPermissionChoices.EDIT_MEMBERS)) {
      permissionsHTML += "<p class='margin-top-1 p--blockquote'><strong class='text-base-dark'>Members:</strong> Can manage members including inviting new members, removing current members, and assigning domains to members.</p>";
    } else if (member_permissions.includes(UserPortfolioPermissionChoices.VIEW_MEMBERS)) {
      permissionsHTML += "<p class='margin-top-1 p--blockquote'><strong class='text-base-dark'>Members (view-only):</strong> Can view all organizational members. Can't manage any members.</p>";
    }

    // If no specific permissions are assigned, display a message indicating no additional permissions
    if (!permissionsHTML) {
      permissionsHTML += "<p class='margin-top-1 p--blockquote'><b>No additional permissions:</b> There are no additional permissions for this member.</p>";
    }

    // Add a permissions header and wrap the entire output in a container
    permissionsHTML = "<div class='desktop:grid-col-7'><h4 class='margin-y-0 text-primary'>Additional permissions for this member</h4>" + permissionsHTML + "</div>";
    
    return permissionsHTML;
  }

  /**
     * Loads rows in the members list, as well as updates pagination around the members list
     * based on the supplied attributes.
     * @param {*} page - the page number of the results (starts with 1)
     * @param {*} sortBy - the sort column option
     * @param {*} order - the sort order {asc, desc}
     * @param {*} scroll - control for the scrollToElement functionality
     * @param {*} searchTerm - the search term
     * @param {*} portfolio - the portfolio id
     */
  loadTable(page, sortBy = this.currentSortBy, order = this.currentOrder, scroll = this.scrollToTable, searchTerm =this.currentSearchTerm, portfolio = this.portfolioValue) {

      // --------- SEARCH
      let searchParams = new URLSearchParams(
        {
          "page": page,
          "sort_by": sortBy,
          "order": order,
          "search_term": searchTerm
        }
      );
      if (portfolio)
        searchParams.append("portfolio", portfolio)


      // --------- FETCH DATA
      // fetch json of page of domains, given params
      let baseUrl = document.getElementById("get_members_json_url");
      if (!baseUrl) {
        return;
      }

      let baseUrlValue = baseUrl.innerHTML;
      if (!baseUrlValue) {
        return;
      }
  
      let url = `${baseUrlValue}?${searchParams.toString()}` //TODO: uncomment for search function
      fetch(url)
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error('Error in AJAX call: ' + data.error);
            return;
          }

          // handle the display of proper messaging in the event that no members exist in the list or search returns no results
          this.updateDisplay(data, this.tableWrapper, this.noTableWrapper, this.noSearchResultsWrapper, this.currentSearchTerm);

          // identify the DOM element where the domain list will be inserted into the DOM
          const memberList = document.querySelector('#members tbody');
          memberList.innerHTML = '';

          const UserPortfolioPermissionChoices = data.UserPortfolioPermissionChoices;
          const invited = 'Invited';
          const invalid_date = 'Invalid date';

          data.members.forEach(member => {
            const member_id = member.source + member.id;
            const member_name = member.name;
            const member_display = member.member_display;
            const member_permissions = member.permissions;
            const domain_urls = member.domain_urls;
            const domain_names = member.domain_names;
            const num_domains = domain_urls.length;
            
            const last_active = this.handleLastActive(member.last_active);

            const action_url = member.action_url;
            const action_label = member.action_label;
            const svg_icon = member.svg_icon;
      
            const row = document.createElement('tr');

            let admin_tagHTML = ``;
            if (member.is_admin)
              admin_tagHTML = `<span class="usa-tag margin-left-1 bg-primary">Admin</span>`

            // generate html blocks for domains and permissions for the member
            let domainsHTML = this.generateDomainsHTML(num_domains, domain_names, domain_urls, action_url);
            let permissionsHTML = this.generatePermissionsHTML(member_permissions, UserPortfolioPermissionChoices);
            
            // domainsHTML block and permissionsHTML block need to be wrapped with hide/show toggle, Expand
            let showMoreButton = '';
            const showMoreRow = document.createElement('tr');
            if (domainsHTML || permissionsHTML) {
              showMoreButton = `
                <button 
                  type="button" 
                  class="usa-button--show-more-button usa-button usa-button--unstyled display-block margin-top-1" 
                  data-for=${member_id}
                  aria-label="Expand for additional information"
                >
                  <span>Expand</span>
                  <svg class="usa-icon usa-icon--big" aria-hidden="true" focusable="false" role="img" width="24">
                    <use xlink:href="/public/img/sprite.svg#expand_more"></use>
                  </svg>
                </button>
              `;

              showMoreRow.innerHTML = `<td colspan='3' headers="header-member row-header-${member_id}" class="padding-top-0"><div class='grid-row'>${domainsHTML} ${permissionsHTML}</div></td>`;
              showMoreRow.classList.add('show-more-content');
              showMoreRow.classList.add('display-none');
              showMoreRow.id = member_id;
            }

            row.innerHTML = `
              <th role="rowheader" headers="header-member" data-label="member email" id='row-header-${member_id}'>
                ${member_display} ${admin_tagHTML} ${showMoreButton}
              </th>
              <td headers="header-last-active row-header-${member_id}" data-sort-value="${last_active.sort_value}" data-label="last_active">
                ${last_active.display_value}
              </td>
              <td headers="header-action row-header-${member_id}">
                <a href="${action_url}">
                  <svg class="usa-icon" aria-hidden="true" focusable="false" role="img" width="24">
                    <use xlink:href="/public/img/sprite.svg#${svg_icon}"></use>
                  </svg>
                  ${action_label} <span class="usa-sr-only">${member_name}</span>
                </a>
              </td>
            `;
            memberList.appendChild(row);
            if (domainsHTML || permissionsHTML) {
              memberList.appendChild(showMoreRow);
            }
          });

          this.initShowMoreButtons();

          // Do not scroll on first page load
          if (scroll)
            ScrollToElement('class', 'members');
          this.scrollToTable = true;

          // update pagination
          this.updatePagination(
            'member',
            '#members-pagination',
            '#members-pagination .usa-pagination__counter',
            '#members',
            data.page,
            data.num_pages,
            data.has_previous,
            data.has_next,
            data.total,
          );
          this.currentSortBy = sortBy;
          this.currentOrder = order;
          this.currentSearchTerm = searchTerm;
      })
      .catch(error => console.error('Error fetching members:', error));
  }
}

class MemberDomainsTable extends LoadTableBase {

  constructor() {
    super('member-domains');
    this.currentSortBy = 'name';
  }
  /**
     * Loads rows in the members list, as well as updates pagination around the members list
     * based on the supplied attributes.
     * @param {*} page - the page number of the results (starts with 1)
     * @param {*} sortBy - the sort column option
     * @param {*} order - the sort order {asc, desc}
     * @param {*} scroll - control for the scrollToElement functionality
     * @param {*} searchTerm - the search term
     * @param {*} portfolio - the portfolio id
     */
  loadTable(page, sortBy = this.currentSortBy, order = this.currentOrder, scroll = this.scrollToTable, searchTerm =this.currentSearchTerm, portfolio = this.portfolioValue) {

      // --------- SEARCH
      let searchParams = new URLSearchParams(
        {
          "page": page,
          "sort_by": sortBy,
          "order": order,
          "search_term": searchTerm,
        }
      );

      let emailValue = this.portfolioElement ? this.portfolioElement.getAttribute('data-email') : null;
      let memberIdValue = this.portfolioElement ? this.portfolioElement.getAttribute('data-member-id') : null;
      let memberOnly = this.portfolioElement ? this.portfolioElement.getAttribute('data-member-only') : null;

      if (portfolio)
        searchParams.append("portfolio", portfolio)
      if (emailValue)
        searchParams.append("email", emailValue)
      if (memberIdValue)
        searchParams.append("member_id", memberIdValue)
      if (memberOnly)
        searchParams.append("member_only", memberOnly)


      // --------- FETCH DATA
      // fetch json of page of domais, given params
      let baseUrl = document.getElementById("get_member_domains_json_url");
      if (!baseUrl) {
        return;
      }

      let baseUrlValue = baseUrl.innerHTML;
      if (!baseUrlValue) {
        return;
      }
  
      let url = `${baseUrlValue}?${searchParams.toString()}` //TODO: uncomment for search function
      fetch(url)
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error('Error in AJAX call: ' + data.error);
            return;
          }

          // handle the display of proper messaging in the event that no members exist in the list or search returns no results
          this.updateDisplay(data, this.tableWrapper, this.noTableWrapper, this.noSearchResultsWrapper, this.currentSearchTerm);

          // identify the DOM element where the domain list will be inserted into the DOM
          const memberDomainsList = document.querySelector('#member-domains tbody');
          memberDomainsList.innerHTML = '';


          data.domains.forEach(domain => {
            const row = document.createElement('tr');

            row.innerHTML = `
              <td scope="row" data-label="Domain name">
                ${domain.name}
              </td>
            `;
            memberDomainsList.appendChild(row);
          });

          // Do not scroll on first page load
          if (scroll)
            ScrollToElement('class', 'member-domains');
          this.scrollToTable = true;

          // update pagination
          this.updatePagination(
            'member domain',
            '#member-domains-pagination',
            '#member-domains-pagination .usa-pagination__counter',
            '#member-domains',
            data.page,
            data.num_pages,
            data.has_previous,
            data.has_next,
            data.total,
          );
          this.currentSortBy = sortBy;
          this.currentOrder = order;
          this.currentSearchTerm = searchTerm;
      })
      .catch(error => console.error('Error fetching domains:', error));
  }
}


/**
 * An IIFE that listens for DOM Content to be loaded, then executes.  This function
 * initializes the domains list and associated functionality.
 *
 */
document.addEventListener('DOMContentLoaded', function() {
  const isDomainsPage = document.getElementById("domains") 
  if (isDomainsPage){
    const domainsTable = new DomainsTable();
    if (domainsTable.tableWrapper) {
      // Initial load
      domainsTable.loadTable(1);
    }
  }
});

/**
 * An IIFE that listens for DOM Content to be loaded, then executes. This function
 * initializes the domain requests list and associated functionality.
 *
 */
document.addEventListener('DOMContentLoaded', function() {
  const domainRequestsSectionWrapper = document.getElementById('domain-requests');
  if (domainRequestsSectionWrapper) {
    const domainRequestsTable = new DomainRequestsTable();
    if (domainRequestsTable.tableWrapper) {
      domainRequestsTable.loadTable(1);
    }
  }

  document.addEventListener('focusin', function(event) {
    closeOpenAccordions(event);
  });
  
  document.addEventListener('click', function(event) {
    closeOpenAccordions(event);
  });

  function closeMoreActionMenu(accordionThatIsOpen) {
    if (accordionThatIsOpen.getAttribute("aria-expanded") === "true") {
      accordionThatIsOpen.click();
    }
  }

  function closeOpenAccordions(event) {
    const openAccordions = document.querySelectorAll('.usa-button--more-actions[aria-expanded="true"]');
    openAccordions.forEach((openAccordionButton) => {
      // Find the corresponding accordion
      const accordion = openAccordionButton.closest('.usa-accordion--more-actions');
      if (accordion && !accordion.contains(event.target)) {
        // Close the accordion if the click is outside
        closeMoreActionMenu(openAccordionButton);
      }
    });
  }
});

const utcDateString = (dateString) => {
  const date = new Date(dateString);
  const utcYear = date.getUTCFullYear();
  const utcMonth = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
  const utcDay = date.getUTCDate().toString().padStart(2, '0');
  let utcHours = date.getUTCHours();
  const utcMinutes = date.getUTCMinutes().toString().padStart(2, '0');

  const ampm = utcHours >= 12 ? 'PM' : 'AM';
  utcHours = utcHours % 12 || 12;  // Convert to 12-hour format, '0' hours should be '12'

  return `${utcMonth} ${utcDay}, ${utcYear}, ${utcHours}:${utcMinutes} ${ampm} UTC`;
};



/**
 * An IIFE that listens for DOM Content to be loaded, then executes.  This function
 * initializes the members list and associated functionality.
 *
 */
document.addEventListener('DOMContentLoaded', function() {
  const isMembersPage = document.getElementById("members") 
  if (isMembersPage){
    const membersTable = new MembersTable();
    if (membersTable.tableWrapper) {
      // Initial load
      membersTable.loadTable(1);
    }
  }
});

/**
 * An IIFE that listens for DOM Content to be loaded, then executes.  This function
 * initializes the member domains list and associated functionality.
 *
 */
document.addEventListener('DOMContentLoaded', function() {
  const isMemberDomainsPage = document.getElementById("member-domains") 
  if (isMemberDomainsPage){
    const memberDomainsTable = new MemberDomainsTable();
    if (memberDomainsTable.tableWrapper) {
      // Initial load
      memberDomainsTable.loadTable(1);
    }
  }
});

/**
 * An IIFE that displays confirmation modal on the user profile page
 */
(function userProfileListener() {

  const showConfirmationModalTrigger = document.querySelector('.show-confirmation-modal');
  if (showConfirmationModalTrigger) {
    showConfirmationModalTrigger.click();
  }
}
)();

/**
 * An IIFE that hooks up the edit buttons on the finish-user-setup page
 */
(function finishUserSetupListener() {

  function getInputField(fieldName){
    return document.querySelector(`#id_${fieldName}`)
  }

  // Shows the hidden input field and hides the readonly one
  function showInputFieldHideReadonlyField(fieldName, button) {
    let inputField = getInputField(fieldName)
    let readonlyField = document.querySelector(`#${fieldName}__edit-button-readonly`)

    readonlyField.classList.toggle('display-none');
    inputField.classList.toggle('display-none');

    // Toggle the bold style on the grid row
    let gridRow = button.closest(".grid-col-2").closest(".grid-row")
    if (gridRow){
      gridRow.classList.toggle("bold-usa-label")
    }
  }

  function handleFullNameField(fieldName = "full_name") {
    // Remove the display-none class from the nearest parent div
    let nameFieldset = document.querySelector("#profile-name-group");
    if (nameFieldset){
      nameFieldset.classList.remove("display-none");
    }

    // Hide the "full_name" field
    let inputField = getInputField(fieldName);
    if (inputField) {
      inputFieldParentDiv = inputField.closest("div");
      if (inputFieldParentDiv) {
        inputFieldParentDiv.classList.add("display-none");
      }
    }
  }

  function handleEditButtonClick(fieldName, button){
    button.addEventListener('click', function() {
      // Lock the edit button while this operation occurs
      button.disabled = true

      if (fieldName == "full_name"){
        handleFullNameField();
      }else {
        showInputFieldHideReadonlyField(fieldName, button);
      }
      
      // Hide the button itself
      button.classList.add("display-none");

      // Unlock after it completes
      button.disabled = false
    });
  }

  function setupListener(){

    

    document.querySelectorAll('[id$="__edit-button"]').forEach(function(button) {
      // Get the "{field_name}" and "edit-button"
      let fieldIdParts = button.id.split("__")
      if (fieldIdParts && fieldIdParts.length > 0){
        let fieldName = fieldIdParts[0]
        
        // When the edit button is clicked, show the input field under it
        handleEditButtonClick(fieldName, button);

        let editableFormGroup = button.parentElement.parentElement.parentElement;
        if (editableFormGroup){
          let readonlyField = editableFormGroup.querySelector(".toggleable_input__readonly-field")
          let inputField = document.getElementById(`id_${fieldName}`);
          if (!inputField || !readonlyField) {
            return;
          }

          let inputFieldValue = inputField.value
          if (inputFieldValue || fieldName == "full_name"){
            if (fieldName == "full_name"){
              let firstName = document.querySelector("#id_first_name");
              let middleName = document.querySelector("#id_middle_name");
              let lastName = document.querySelector("#id_last_name");
              if (firstName && lastName && firstName.value && lastName.value) {
                let values = [firstName.value, middleName.value, lastName.value]
                readonlyField.innerHTML = values.join(" ");
              }else {
                let fullNameField = document.querySelector('#full_name__edit-button-readonly');
                let svg = fullNameField.querySelector("svg use")
                if (svg) {
                  const currentHref = svg.getAttribute('xlink:href');
                  if (currentHref) {
                    const parts = currentHref.split('#');
                    if (parts.length === 2) {
                      // Keep the path before '#' and replace the part after '#' with 'invalid'
                      const newHref = parts[0] + '#error';
                      svg.setAttribute('xlink:href', newHref);
                      fullNameField.classList.add("toggleable_input__error")
                      label = fullNameField.querySelector(".toggleable_input__readonly-field")
                      label.innerHTML = "Unknown";
                    }
                  }
                }
              }
              
              // Technically, the full_name field is optional, but we want to display it as required. 
              // This style is applied to readonly fields (gray text). This just removes it, as
              // this is difficult to achieve otherwise by modifying the .readonly property.
              if (readonlyField.classList.contains("text-base")) {
                readonlyField.classList.remove("text-base")
              }
            }else {
              readonlyField.innerHTML = inputFieldValue
            }
          }
        }
      }
    });
  }

  function showInputOnErrorFields(){
    document.addEventListener('DOMContentLoaded', function() {

      // Get all input elements within the form
      let form = document.querySelector("#finish-profile-setup-form");
      let inputs = form ? form.querySelectorAll("input") : null;
      if (!inputs) {
        return null;
      }

      let fullNameButtonClicked = false
      inputs.forEach(function(input) {
        let fieldName = input.name;
        let errorMessage = document.querySelector(`#id_${fieldName}__error-message`);

        // If no error message is found, do nothing
        if (!fieldName || !errorMessage) {
          return null;
        }

        let editButton = document.querySelector(`#${fieldName}__edit-button`);
        if (editButton){
          // Show the input field of the field that errored out 
          editButton.click();
        }

        // If either the full_name field errors out,
        // or if any of its associated fields do - show all name related fields.
        let nameFields = ["first_name", "middle_name", "last_name"];
        if (nameFields.includes(fieldName) && !fullNameButtonClicked){
          // Click the full name button if any of its related fields error out
          fullNameButton = document.querySelector("#full_name__edit-button");
          if (fullNameButton) {
            fullNameButton.click();
            fullNameButtonClicked = true;
          }
        }
      });  
    });
  };

  setupListener();

  // Show the input fields if an error exists
  showInputOnErrorFields();

})();


/**
 * An IIFE that changes the default clear behavior on comboboxes to the input field.
 * We want the search bar to act soley as a search bar.
 */
(function loadInitialValuesForComboBoxes() {
  var overrideDefaultClearButton = true;
  var isTyping = false;

  document.addEventListener('DOMContentLoaded', (event) => {
    handleAllComboBoxElements();
  });

  function handleAllComboBoxElements() {
    const comboBoxElements = document.querySelectorAll(".usa-combo-box");
    comboBoxElements.forEach(comboBox => {
      const input = comboBox.querySelector("input");
      const select = comboBox.querySelector("select");
      if (!input || !select) {
        console.warn("No combobox element found");
        return;
      }
      // Set the initial value of the combobox
      let initialValue = select.getAttribute("data-default-value");
      let clearInputButton = comboBox.querySelector(".usa-combo-box__clear-input");
      if (!clearInputButton) {
        console.warn("No clear element found");
        return;
      }

      // Override the default clear button behavior such that it no longer clears the input,
      // it just resets to the data-initial-value.

      // Due to the nature of how uswds works, this is slightly hacky.

      // Use a MutationObserver to watch for changes in the dropdown list
      const dropdownList = comboBox.querySelector(`#${input.id}--list`);
      const observer = new MutationObserver(function(mutations) {
          mutations.forEach(function(mutation) {
              if (mutation.type === "childList") {
                addBlankOption(clearInputButton, dropdownList, initialValue);
              }
          });
      });

      // Configure the observer to watch for changes in the dropdown list
      const config = { childList: true, subtree: true };
      observer.observe(dropdownList, config);

      // Input event listener to detect typing
      input.addEventListener("input", () => {
        isTyping = true;
      });

      // Blur event listener to reset typing state
      input.addEventListener("blur", () => {
        isTyping = false;
      });

      // Hide the reset button when there is nothing to reset.
      // Do this once on init, then everytime a change occurs.
      updateClearButtonVisibility(select, initialValue, clearInputButton)
      select.addEventListener("change", () => {
        updateClearButtonVisibility(select, initialValue, clearInputButton)
      });

      // Change the default input behaviour - have it reset to the data default instead
      clearInputButton.addEventListener("click", (e) => {
        if (overrideDefaultClearButton && initialValue) {
          e.preventDefault();
          e.stopPropagation();
          input.click();
          // Find the dropdown option with the desired value
          const dropdownOptions = document.querySelectorAll(".usa-combo-box__list-option");
          if (dropdownOptions) {
            dropdownOptions.forEach(option => {
                if (option.getAttribute("data-value") === initialValue) {
                    // Simulate a click event on the dropdown option
                    option.click();
                }
            });
          }
        }
      });
    });
  }

  function updateClearButtonVisibility(select, initialValue, clearInputButton) {
    if (select.value === initialValue) {
      hideElement(clearInputButton);
    }else {
      showElement(clearInputButton)
    }
  }

  function addBlankOption(clearInputButton, dropdownList, initialValue) {
    if (dropdownList && !dropdownList.querySelector('[data-value=""]') && !isTyping) {
        const blankOption = document.createElement("li");
        blankOption.setAttribute("role", "option");
        blankOption.setAttribute("data-value", "");
        blankOption.classList.add("usa-combo-box__list-option");
        if (!initialValue){
          blankOption.classList.add("usa-combo-box__list-option--selected")
        }
        blankOption.textContent = "⎯";

        dropdownList.insertBefore(blankOption, dropdownList.firstChild);
        blankOption.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          overrideDefaultClearButton = false;
          // Trigger the default clear behavior
          clearInputButton.click();
          overrideDefaultClearButton = true;
        });
    }
  }
})();

/** An IIFE that intializes the requesting entity page.
 * This page has a radio button that dynamically toggles some fields
 * Within that, the dropdown also toggles some additional form elements.
*/
(function handleRequestingEntityFieldset() { 
  // Sadly, these ugly ids are the auto generated with this prefix
  const formPrefix = "portfolio_requesting_entity"
  const radioFieldset = document.getElementById(`id_${formPrefix}-requesting_entity_is_suborganization__fieldset`);
  const radios = radioFieldset?.querySelectorAll(`input[name="${formPrefix}-requesting_entity_is_suborganization"]`);
  const select = document.getElementById(`id_${formPrefix}-sub_organization`);
  const suborgContainer = document.getElementById("suborganization-container");
  const suborgDetailsContainer = document.getElementById("suborganization-container__details");
  if (!radios || !select || !suborgContainer || !suborgDetailsContainer) return;

  // requestingSuborganization: This just broadly determines if they're requesting a suborg at all
  // requestingNewSuborganization: This variable determines if the user is trying to *create* a new suborganization or not.
  var requestingSuborganization = Array.from(radios).find(radio => radio.checked)?.value === "True";
  var requestingNewSuborganization = document.getElementById(`id_${formPrefix}-is_requesting_new_suborganization`);

  function toggleSuborganization(radio=null) {
    if (radio != null) requestingSuborganization = radio?.checked && radio.value === "True";
    requestingSuborganization ? showElement(suborgContainer) : hideElement(suborgContainer);
    requestingNewSuborganization.value = requestingSuborganization && select.value === "other" ? "True" : "False";
    requestingNewSuborganization.value === "True" ? showElement(suborgDetailsContainer) : hideElement(suborgDetailsContainer);
  }

  // Add fake "other" option to sub_organization select
  if (select && !Array.from(select.options).some(option => option.value === "other")) {
    select.add(new Option("Other (enter your organization manually)", "other"));
  }

  if (requestingNewSuborganization.value === "True") {
    select.value = "other";
  }

  // Add event listener to is_suborganization radio buttons, and run for initial display
  toggleSuborganization();
  radios.forEach(radio => {
    radio.addEventListener("click", () => toggleSuborganization(radio));
  });

  // Add event listener to the suborg dropdown to show/hide the suborg details section
  select.addEventListener("change", () => toggleSuborganization());
})();
