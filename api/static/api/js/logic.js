var filePath = "";
var type = ""

$(document).ready(function () {
    // $('#jpgchecked').prop('checked', true);
    $('#categoryDropDown').change(function () {
        if ($(this).find("option:selected").val() === 'folder') {
            $('#uploadZip').prop("value", "Choose a zipfile")
        } else {
            $('#uploadZip').prop("value", "Choose File ")
        }
        $("#result").text("");
        $("#selectedFolderText").text("");
    });

    $("#uploadZip").click(function (event) {
        $("#result").html("Processing..").wrap('<pre />');
        //stop submit the form, we will post it manually.
        event.preventDefault();
        $("#uploadZip").prop("disabled", true);
        $("#selectedFolderText").text("");
        $("#showInvalid").prop("disabled", true);
        $("#adminButton").prop("disabled", true);

        var form = $('#fileUploadForm')[0];
        var data = new FormData(form);

        // Get form
        //var form = $('#fileUploadForm')[0];
        // Create an FormData object
        //var data = new FormData(form);
        //data.append("info", "");
        // var selectedValue = $('#categoryDropDown').find("option:selected").val();
        // if (selectedValue === "folder") {
        //     data.append("type", "folder");
        //     type = "folder"
        // }
        // else {
        //     data.append("type", "file");
        //     type = "file"
        // }
        $.ajax({
            type: "POST",
            enctype: 'multipart/form-data',
            url: "/photoValidator/",
            data: data,
            processData: false,
            contentType: false,
            cache: false,
            timeout: 600000,
            success: function (data) {
                filePath = data;
                $("#uploadZip").prop("disabled", false);
                if (data) {
                    $("#result").text("");
                    $("#result").html("Validation completed").wrap('<pre />');
                    $("#btnSubmit").prop("disabled", false);
                    $("#showInvalid").prop("disabled", false);
                    $("#adminButton").prop("disabled", false);
                    $("#selectedFolderText").html(data + "/").wrap('<pre />');
                }
            },
            error: function (e) {
                $("#uploadZip").prop("disabled", false);
            }
        });
    });
    
    $("#btnSubmit").click(function (event) {
        $("#result").html("Processing..").wrap('<pre />');
        //stop submit the form, we will post it manually.
        event.preventDefault();
        // Get form
        var form = $('#fileUploadForm')[0];
        // Create an FormData object
        var data = new FormData(form);
        //data.append("path", filePath);
        //data.append("type", type);
        // If you want to add an extra field for the FormData
        //data.append("CustomField", "This is some extra data, testing");
        // disabled the submit button
        $("#btnSubmit").prop("disabled", true);
        $("#adminButton").prop("disabled", true);
        $("#showInvalid").prop("disabled", true);
        $("#uploadFolder").prop("disabled", true);
        $("#showCSV").prop("disabled", true);
        $.ajax({
            type: "post",
            enctype: 'multipart/form-data',
            url: "/photoValidator/",
            data: data,
            processData: false,
            contentType: false,
            cache: false,
            timeout: 600000,
            success: function (data) {
                if (type === "file")
                    $("#result").css("font-size", "medium");
                $("#result").html(data).wrap('<pre />');;
                console.log("SUCCESS : ", data);
                $("#btnSubmit").prop("disabled", false);
                $("#showInvalid").prop("disabled", false);
                $("#adminButton").prop("disabled", false);
                $("#uploadFolder").prop("disabled", false);
            },
            error: function (e) {
                // {#$("#result").text(e.responseText);#}
                // {#console.log("ERROR : ", e);#}
                // {#$("#btnSubmit").prop("disabled", false);#}
            }
        });

    });



    $("#btnSaveConfig").click(function (event) {
        //stop submit the form, we will post it manually.
        event.preventDefault();
        
        $("#updatebutton").empty().text("Config successfully updated..");
        // $("#updatebutton").html("Config successfully updated..").wrap('<pre />');
        // Get form
        var form = $('#fileUploadForm1')[0];
        // Create an FormData object
        var data = new FormData(form);
        data.append("minHeight", $("#minHeight").val());
        data.append("maxHeight", $("#maxHeight").val());
        data.append("minWidth", $("#minWidth").val());
        data.append("maxWidth", $("#maxWidth").val());
        data.append("minSize", $("#minSize").val());
        data.append("maxSize", $("#maxSize").val());
        // data.append("jpgchecked", $("#jpgchecked").is(":checked"));
        // data.append("pngchecked", $("#pngchecked").is(":checked"));
        // data.append("jpegchecked", $("#jpegchecked").is(":checked"));
        data.append("jpgchecked", $("#jpgchecked").is(":checked") ? 'True' : 'False');
        data.append("pngchecked", $("#pngchecked").is(":checked") ? 'True' : 'False');
        data.append("jpegchecked", $("#jpegchecked").is(":checked") ? 'True' : 'False');
        //data.append("CustomField", "This is some extra data, testing");
        // disabled the submit button
        $.ajax({
            type: "POST",
            enctype: 'multipart/form-data',
            url: "/saveConfig/",
            data: data,
            processData: false,
            contentType: false,
            cache: false,
            timeout: 600000,
            success: function (data) {
            },
            error: function (e) {
                // {#$("#result").text(e.responseText);#}
                // {#console.log("ERROR : ", e);#}
                // {#$("#btnSubmit").prop("disabled", false);#}
            }
        });
    });
    //             $('#SpaceAccommodation').change(function () {
    //     var selectedText = $(this).find("option:selected").text();
    //
    //     $("").text(selectedText);
    // });
});