async function submitRequest(){

    const email=document.getElementById("email").value;

    const duration=document.getElementById("duration").value;

    const reason=document.getElementById("reason").value;

    const response=await fetch(
        "https://fyl80dkj6i.execute-api.ap-south-1.amazonaws.com/request",
        {
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                user_email:email,
                duration_hours:Number(duration),
                justification:reason
            })
        });

    const data=await response.json();

    document.getElementById("result").innerHTML=data.message;
}