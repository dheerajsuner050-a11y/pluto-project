while True:

    try:
        people = int(input("\nकितने लोगों के लिए खाना बनाना है? "))

        if people <= 0:
            print("कृपया 0 से अधिक लोगों की संख्या डालें.")
            continue

        calculate_catering(people)

        again = input("\nक्या दूसरी संख्या के लिए calculation करें? (y/n): ")

        if again.lower() != "y":
            print("\nCalculator बंद किया गया.")
            break

    except ValueError:
        print("कृपया केवल संख्या डालें.")
