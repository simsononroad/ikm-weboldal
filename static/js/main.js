function copyToClipboard(name, title) {
    // A dollárjel ($) törölve, csak a ` karakter maradt
    const szoveg = `Szia! Meg szeretném vásárolni a ${name} matricát ami ${title} Ft-ért van kitéve a weboldalra. Üdvözlettel: (A te neved)`;
    
    navigator.clipboard.writeText(szoveg).then(() => {
        alert("Másolva a vágólapra! Most már beillesztheted Instagram üzenetbe.");
        if (confirm("Instagram megnyitása")){
            window.open("https://www.instagram.com/illegalis_kismotorosok/", "_blank")
        }
    }).catch(err => {
        console.error("Hiba a másolás során: ", err);
        alert("Hiba történt a másoláskor.");
    });
}