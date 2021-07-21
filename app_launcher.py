import argparse

from dashboard.ariadne_dashboard import launch

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ariadne Dashboard launcher')
    parser.add_argument('-d', dest='debug', type=bool, default=False, help='launch dashboard in debug mode')
    # parser.add_argument('-p', dest='savepath', type=str, default='.', help='savepath for orbit dumps')
    
    args = parser.parse_args()
    launch(args.debug)
