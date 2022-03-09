function initAutocomplete() {
    // Create the autocomplete object, restricting the search to geographical
    // location types.
    autocompleteOrigin = new google.maps.places.Autocomplete(
      /** @type {!HTMLInputElement} */(document.getElementById('autocompleteOrigin')),
      {types: ['geocode']});

    autocompleteDestination = new google.maps.places.Autocomplete(
       /** @type {!HTMLInputElement} */(document.getElementById('autocompleteDestination')),
       {types: ['geocode']});
    // When the user selects an address from the dropdown, populate the address
    // fields in the form.
    autocompleteOrigin.addListener('place_changed', fillInAddress);
    autocompleteDestination.addListener('place_changed', fillInAddress);
}

/* Set the width of the sidebar to 250px and the left margin of the page content to 250px */
function openNav() {
  document.getElementById("mySidebar").style.width = "250px";
  document.getElementById("main").style.marginLeft = "250px";
}

/* Set the width of the sidebar to 0 and the left margin of the page content to 0 */
function closeNav() {
  document.getElementById("mySidebar").style.width = "0";
  document.getElementById("main").style.marginLeft = "0";
}
