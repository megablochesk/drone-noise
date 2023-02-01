for dir in recourses/results/experiments/*/
do
    dir=${dir%*/}      # remove the trailing "/"
    echo ""
    echo "----------------------------${dir##*/}"    # print everything after the final "/"
    python3 visual.py ${dir##*/}    # print everything after the final "/"
done
