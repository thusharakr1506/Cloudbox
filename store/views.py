import razorpay

from django.shortcuts import render,redirect
from django.views.generic import View,TemplateView
from django.contrib.auth import authenticate,login,logout
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt 

from store.forms import RegistrationForm,LoginForm
from store.models import Product,BasketItem,Size,Order,OrderItems
from store.decorators import signin_required,owner_permission_required

KEY_ID=""
KEY_SECRET=""

# url:localhost:8000/register/
# method:get,post
# form_class:RegistrationForm

class SignUpView(View):


    def get(self,request,*args,**kwargs):
        form=RegistrationForm()
        return render(request,"register.html",{"form":form})
    def post(self,request,*args,**kwargs):
        form=RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("signin")
        return render(request,"login.html",{"form":form})
    
# url:localhost:8000/
# method:get,post
# form_class:LoginForm
    
class SignInView(View):
    def get(self,request,*args,**kwargs):
        form=LoginForm()
        return render(request,"login.html",{"form":form})
    
    def post(self,request,*args,**kwargs):
        form=LoginForm(request.POST)
        if form.is_valid():
            u_name=form.cleaned_data.get("username")
            pwd=form.cleaned_data.get("password")
            user_object=authenticate(request,username=u_name,password=pwd)
            if user_object:
                login(request,user_object)
                return redirect("index")
        messages.error(request,"invalid credentials")
        return render(request,"login.html",{"form":form})

@method_decorator([signin_required,never_cache],name="dispatch")    
class IndexView(View):
    def get(self,request,*args,**kwargs):
        qs=Product.objects.all()
        return render(request,"index.html",{"data":qs})


@method_decorator([signin_required,never_cache],name="dispatch")    
class ProductDetailView(View):
    
    def get(self,request,*args,**kwargs):
        id=kwargs.get("pk")
        qs=Product.objects.get(id=id)
        return render(request, "product_detail.html",{"data":qs})
    

class HomeView(TemplateView):
    template_name="base.html"

# add to basket
# url:localhost:8000/products/{id}/add_to_basket/
# method:post 

@method_decorator([signin_required,never_cache],name="dispatch")    
class AddToBasketView(View):

    def post(self,request,*args,**kwargs):
        size=request.POST.get("size")
        size_obj=Size.objects.get(name=size)
        qty=request.POST.get("qty")
        id=kwargs.get("pk")
        product_obj=Product.objects.get(id=id)
        BasketItem.objects.create(
            size_object=size_obj,
            qty=qty,
            product_object=product_obj,
            basket_object=request.user.cart
        )
        return redirect("index")


@method_decorator([signin_required,never_cache],name="dispatch")       
class BasketItemListView(View):

    def get(self,request,*args,**kwargs):
        qs=request.user.cart.cartitem.filter(is_order_placed=False)
        return render(request,"cart-list.html",{"data":qs})
    

@method_decorator([signin_required,owner_permission_required,never_cache],name="dispatch")        
class BasketItemRemoveView(View):

    def get(self,request,*args,**kwargs):
        id=kwargs.get("pk")
        basket_item_object=BasketItem.objects.get(id=id)
        basket_item_object.delete()
        return redirect("basket-item")
    

@method_decorator([signin_required,owner_permission_required,never_cache],name="dispatch")        
class CartItemUpdateQuantityView(View):

    def post(self,request,*args,**kwargs):
        action=request.POST.get("counterbutton")
        print(action)
        id=kwargs.get("pk")
        basket_item_object=BasketItem.objects.get(id=id)

        if action=="+":
            basket_item_object.qty+=1
            basket_item_object.save()
        else:
            basket_item_object.qty-=1
            basket_item_object.save()
            
        return redirect("basket-item")


@method_decorator([signin_required,never_cache],name="dispatch")       
class CheckOutView(View):
    
    def get(self,request,*args,**kwargs):
        return render(request,"checkout.html")
    
    def post(self,request,*args,**kwargs):
        email=request.POST.get("email")
        phone=request.POST.get("phone")
        address=request.POST.get("address")
        payment_method=request.POST.get("payment")

        # creating order_instance

        order_obj=Order.objects.create(
            user_object=request.user,
            delivery_address=address,
            phone=phone,
            email=email,
            total=request.user.cart.basket_total,
            payment=payment_method
        )

        # creating order_item_instance

        try:
            basket_items=request.user.cart.cart_items
            for bi in basket_items:
                OrderItems.objects.create(
                    order_object=order_obj,
                    basket_item_object=bi

                )
                bi.is_order_placed=True
                bi.save()
                # print("text block 1")

            
        except:
            order_obj.delete()

        finally:
            # print("text block 2")
            print(payment_method)
            print(order_obj)
            if payment_method=="online" and order_obj:
                # print("text block 3")
                client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

                data = { "amount": order_obj.get_order_total*100, "currency": "INR", "receipt": "order_rcptid_11" }

                payment = client.order.create(data=data)        

                print("payment initiate",payment)
                context={
                    "key":KEY_ID,
                    "order_id":payment.get("id"),
                    "amount":payment.get("amount")
                }
                return render(request,"payment.html",{"context":context})

            return redirect("index")
        
@method_decorator(csrf_exempt,name="dispatch")
class PaymentVerificationView(View):

    def post(self,request,*args,**kwargs):
        
        print("==================",request.POST)
        return render(request,"success.html")


@method_decorator([signin_required,never_cache],name="dispatch")       
class SignOutView(View):
    
    def get(self,request,*args,**kwargs):
        logout(request)
        return redirect("signin")
    

class OrderSummaryView(View):

    def get(self,request,*args,**kwargs):
        qs=Order.objects.filter(user_object=request.user).exclude(status="cancelled")
        return render(request,"order_summary.html",{"data":qs})
    
class OrderItemRemoveView(View):

    def get(self,request,*args,**kwargs):
        id=kwargs.get("pk")
        OrderItems.objects.get(id=id).delete()
        return redirect("order-summary")
    




# {
#     'id': 'order_NlOOvsr9d3GYgp',
#     'entity': 'order',
#     'amount': 239800,
#     'amount_paid': 0,
#     'amount_due': 239800,
#     'currency': 'INR', 
#     'receipt': 'order_rcptid_11', 
#     'offer_id': None, 
#     'status': 'created', 
#     'attempts': 0, 
#     'notes': [], 
#     'created_at': 1710235310
#     }  
