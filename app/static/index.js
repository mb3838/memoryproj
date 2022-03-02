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
