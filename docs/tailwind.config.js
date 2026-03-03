tailwind.config = {
      theme: {
        extend: {
          colors: {
            limon: '#fcc41d'
          },
          boxShadow: {
            glow: '0 0 40px rgba(252,196,29,0.35)'
          },
          animation: {
            float: 'float 6s ease-in-out infinite'
          },
          keyframes: {
            float: {
              '0%, 100%': { transform: 'translateY(0px)' },
              '50%': { transform: 'translateY(-15px)' }
            }
          }
        }
      }
    }